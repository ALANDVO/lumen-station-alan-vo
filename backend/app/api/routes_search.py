"""FTS5 chunk search and inspection endpoints."""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import Dict, Any

from app.core.security import require_role
from app.models.schemas import SearchQuery, SearchResponse, SearchResultItem
from app.services.search_index import search_chunks
from app.core.database import get_db

router = APIRouter(prefix="/api/search", tags=["search"])


@router.post("", response_model=SearchResponse)
def search_indexed_chunks(
    req: SearchQuery,
    user: Dict[str, Any] = Depends(require_role("viewer")),
) -> Dict[str, Any]:
    """
    Search indexed tool execution output chunks via SQLite FTS5.
    Returns ranked snippets with BM25 scoring.
    """
    matches = search_chunks(
        query=req.query,
        session_id=req.session_id,
        limit=req.limit,
    )

    items = [
        SearchResultItem(
            chunk_id=m["chunk_id"],
            execution_id=m["execution_id"],
            chunk_index=m["chunk_index"],
            chunk_type=m["chunk_type"],
            snippet=m["snippet"],
            token_count=m["token_count"],
        )
        for m in matches
    ]

    return {
        "query": req.query,
        "total_matches": len(items),
        "results": items,
    }


@router.get("/chunks/{chunk_id}")
def get_chunk_content(
    chunk_id: str,
    user: Dict[str, Any] = Depends(require_role("viewer")),
) -> Dict[str, Any]:
    """Inspect full raw content of a specific indexed chunk."""
    with get_db() as conn:
        row = conn.execute("""
            SELECT id, execution_id, chunk_index, chunk_type, content, byte_size, token_count, created_at
            FROM execution_chunks
            WHERE id = ?;
        """, (chunk_id,)).fetchone()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Chunk '{chunk_id}' not found.",
            )

        return {
            "id": row["id"],
            "execution_id": row["execution_id"],
            "chunk_index": row["chunk_index"],
            "chunk_type": row["chunk_type"],
            "content": row["content"],
            "byte_size": row["byte_size"],
            "token_count": row["token_count"],
            "created_at": row["created_at"],
        }
