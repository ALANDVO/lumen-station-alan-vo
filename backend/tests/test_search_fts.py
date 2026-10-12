"""Tests for bounded chunk splitting and FTS5 search indexing."""

import pytest
from app.services.search_index import split_into_bounded_chunks, search_chunks, index_execution_chunks
from app.core.database import get_db
import uuid


def test_bounded_chunk_splitting_respects_limit():
    """Verify that chunks never exceed specified byte limits."""
    large_line = "A" * 1000 + "\n"
    text = large_line * 20  # ~20,000 bytes

    chunks = split_into_bounded_chunks(text, max_bytes=2048)
    assert len(chunks) > 1

    for chunk_type, chunk_content in chunks:
        assert len(chunk_content.encode("utf-8")) <= 2048


def test_fts5_indexing_and_search_retrieval():
    """Verify FTS5 full text indexing and snippet retrieval."""
    exec_id = str(uuid.uuid4())
    sess_id = "sess-search-" + str(uuid.uuid4())
    sample_text = (
        "Starting compiler pipeline...\n"
        "ERROR 404: Missing symbol ReactDomClient in module bundle.\n"
        "Build terminated with exit code 1.\n"
    )

    with get_db() as conn:
        conn.execute("""
            INSERT INTO sessions (id, platform, working_dir, os_name, quiet_mode, created_at, updated_at)
            VALUES (?, 'generic', '.', 'linux', 0, '2026-10-12T15:00:00Z', '2026-10-12T15:00:00Z');
        """, (sess_id,))
        conn.execute("""
            INSERT INTO executions (
                id, session_id, command, exit_code, duration_ms, raw_bytes, raw_tokens,
                compact_bytes, compact_tokens, savings_ratio, status, error, created_at
            ) VALUES (?, ?, 'build', 1, 10.0, 100, 20, 100, 20, 0.0, 'completed', NULL, '2026-10-12T15:00:00Z');
        """, (exec_id, sess_id))
        index_execution_chunks(conn, exec_id, sample_text)

    results = search_chunks("ReactDomClient")
    assert len(results) >= 1
    found = any(r["execution_id"] == exec_id for r in results)
    assert found


def test_search_empty_and_special_characters():
    """Verify graceful handling of empty or punctuation-only search queries."""
    assert search_chunks("") == []
    assert search_chunks("   ") == []
    assert search_chunks("!@#$%^&*()") == []
