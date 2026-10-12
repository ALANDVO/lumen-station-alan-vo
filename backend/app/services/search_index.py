"""FTS5 search indexing and chunk retrieval service."""

import sqlite3
import uuid
from typing import List, Dict, Any, Tuple
from datetime import datetime, timezone
from app.core.config import settings
from app.core.database import get_db


def estimate_tokens(text: str) -> int:
    """Deterministic token estimation (heuristic ~4 chars per token plus punctuation weighting)."""
    if not text:
        return 0
    words = len(text.split())
    chars = len(text)
    # Blended character/word estimation aligned with typical BPE models
    return max(1, int((chars / 4.0 * 0.7) + (words * 1.3 * 0.3)))


def split_into_bounded_chunks(content: str, max_bytes: int | None = None) -> List[Tuple[str, str]]:
    """
    Split text into chunks bounded by max_bytes to avoid SQLite FTS bloat.
    Returns list of (chunk_type, chunk_text).
    """
    limit = max_bytes or settings.max_chunk_bytes
    if not content:
        return [("empty", "")]

    lines = content.splitlines(keepends=True)
    chunks: List[Tuple[str, str]] = []
    current_lines: List[str] = []
    current_bytes = 0

    for line in lines:
        line_bytes = len(line.encode("utf-8"))
        # If a single line exceeds the limit, hard-slice it
        if line_bytes > limit:
            if current_lines:
                chunks.append(("standard", "".join(current_lines)))
                current_lines = []
                current_bytes = 0
            # Sliced sub-lines
            encoded = line.encode("utf-8")
            for i in range(0, len(encoded), limit):
                sub_text = encoded[i:i + limit].decode("utf-8", errors="replace")
                chunks.append(("large_slice", sub_text))
            continue

        if current_bytes + line_bytes > limit:
            chunks.append(("standard", "".join(current_lines)))
            current_lines = [line]
            current_bytes = line_bytes
        else:
            current_lines.append(line)
            current_bytes += line_bytes

    if current_lines:
        chunks.append(("standard", "".join(current_lines)))

    return chunks


def index_execution_chunks(conn: sqlite3.Connection, execution_id: str, content: str) -> int:
    """Index execution output chunks into SQLite and FTS5 table."""
    chunks = split_into_bounded_chunks(content)
    now = datetime.now(timezone.utc).isoformat()

    for idx, (chunk_type, chunk_text) in enumerate(chunks):
        chunk_id = str(uuid.uuid4())
        byte_size = len(chunk_text.encode("utf-8"))
        tok_count = estimate_tokens(chunk_text)

        conn.execute("""
            INSERT INTO execution_chunks (id, execution_id, chunk_index, chunk_type, content, byte_size, token_count, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """, (chunk_id, execution_id, idx, chunk_type, chunk_text, byte_size, tok_count, now))

        # Index in FTS5
        conn.execute("""
            INSERT INTO fts_chunks (chunk_id, execution_id, content)
            VALUES (?, ?, ?);
        """, (chunk_id, execution_id, chunk_text))

    return len(chunks)


def search_chunks(query: str, session_id: str | None = None, limit: int = 10) -> List[Dict[str, Any]]:
    """Execute ranked FTS5 search query across indexed output chunks."""
    safe_query = "".join(c for c in query if c.isalnum() or c in " _-*").strip()
    if not safe_query:
        return []

    fts_terms = " OR ".join(f'"{term}"' for term in safe_query.split() if term)
    if not fts_terms:
        return []

    with get_db() as conn:
        if session_id:
            sql = """
                SELECT 
                    c.id as chunk_id,
                    c.execution_id,
                    c.chunk_index,
                    c.chunk_type,
                    snippet(fts_chunks, 2, '<b>', '</b>', '...', 32) as snippet_text,
                    c.token_count
                FROM fts_chunks
                JOIN execution_chunks c ON fts_chunks.chunk_id = c.id
                JOIN executions e ON c.execution_id = e.id
                WHERE fts_chunks MATCH ? AND e.session_id = ?
                ORDER BY rank
                LIMIT ?;
            """
            cursor = conn.execute(sql, (fts_terms, session_id, limit))
        else:
            sql = """
                SELECT 
                    c.id as chunk_id,
                    c.execution_id,
                    c.chunk_index,
                    c.chunk_type,
                    snippet(fts_chunks, 2, '<b>', '</b>', '...', 32) as snippet_text,
                    c.token_count
                FROM fts_chunks
                JOIN execution_chunks c ON fts_chunks.chunk_id = c.id
                WHERE fts_chunks MATCH ?
                ORDER BY rank
                LIMIT ?;
            """
            cursor = conn.execute(sql, (fts_terms, limit))

        results = []
        for row in cursor.fetchall():
            results.append({
                "chunk_id": row["chunk_id"],
                "execution_id": row["execution_id"],
                "chunk_index": row["chunk_index"],
                "chunk_type": row["chunk_type"],
                "snippet": row["snippet_text"],
                "token_count": row["token_count"],
            })
        return results
