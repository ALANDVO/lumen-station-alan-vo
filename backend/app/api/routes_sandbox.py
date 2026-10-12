"""Tool output sandboxing and execution endpoints."""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import Dict, Any, List, Optional

from app.core.security import require_role, verify_csrf_write, get_current_user
from app.models.schemas import (
    ExecutionRequest,
    ExecutionResponse,
    ExecutionDetail,
    AdvisoryExplanationRequest,
    AdvisoryExplanationResponse,
)
from app.services.sandbox_engine import execute_sandboxed_command, get_execution_detail
from app.services.lifecycle_manager import abort_execution
from app.services.llm_client import request_advisory_explanation
from app.services.audit_service import log_audit_event
from app.core.database import get_db

router = APIRouter(prefix="/api/sandbox", tags=["sandbox"])


@router.post("/execute", response_model=ExecutionResponse, dependencies=[Depends(verify_csrf_write)])
def run_tool_execution(
    req: ExecutionRequest,
    user: Dict[str, Any] = Depends(require_role("operator")),
) -> Dict[str, Any]:
    """
    Run command inside the sandboxed execution environment with hard timeout budget.
    Automatically summarizes verbose outputs and indexes chunks in SQLite FTS5.
    """
    result = execute_sandboxed_command(
        session_id=req.session_id,
        command=req.command,
        working_dir=req.working_dir,
        timeout_seconds=req.timeout_seconds,
        head_lines=req.head_lines,
        tail_lines=req.tail_lines,
    )

    log_audit_event(
        user_email=user.get("email", "unknown"),
        action="TOOL_EXECUTION",
        resource_type="execution",
        resource_id=result["id"],
        details={
            "command": req.command,
            "savings_ratio": result["savings_ratio"],
            "raw_tokens": result["raw_tokens"],
            "compact_tokens": result["compact_tokens"],
        },
    )

    return result


@router.get("/executions/{execution_id}", response_model=ExecutionDetail)
def get_execution(
    execution_id: str,
    user: Dict[str, Any] = Depends(require_role("viewer")),
) -> Dict[str, Any]:
    """Retrieve execution detail and folded summary."""
    detail = get_execution_detail(execution_id)
    if not detail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Execution record '{execution_id}' not found.",
        )
    return detail


@router.post("/executions/{execution_id}/abort", dependencies=[Depends(verify_csrf_write)])
def abort_active_execution(
    execution_id: str,
    user: Dict[str, Any] = Depends(require_role("operator")),
) -> Dict[str, Any]:
    """
    Abort an in-flight tool execution (resolves issue #959).
    Cleanly escalates SIGTERM to SIGKILL.
    """
    aborted = abort_execution(execution_id)
    if not aborted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active in-flight execution process found for ID '{execution_id}'.",
        )

    log_audit_event(
        user_email=user.get("email", "unknown"),
        action="ABORT_EXECUTION",
        resource_type="execution",
        resource_id=execution_id,
        details={},
    )

    return {"message": "Execution process aborted successfully", "execution_id": execution_id}


@router.post("/executions/{execution_id}/explain", response_model=AdvisoryExplanationResponse)
async def explain_execution(
    execution_id: str,
    req: AdvisoryExplanationRequest,
    user: Dict[str, Any] = Depends(require_role("viewer")),
) -> Dict[str, Any]:
    """
    Generate an opt-in advisory explanation grounded strictly in the tool record.
    Works offline deterministically when no LLM key is configured.
    """
    detail = get_execution_detail(execution_id)
    if not detail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Execution record '{execution_id}' not found.",
        )

    return await request_advisory_explanation(detail, focus=req.focus or "summary")


@router.get("/executions", response_model=List[ExecutionResponse])
def list_executions(
    session_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    user: Dict[str, Any] = Depends(require_role("viewer")),
) -> List[Dict[str, Any]]:
    """List executions with optional session filtering."""
    with get_db() as conn:
        if session_id:
            cursor = conn.execute("""
                SELECT * FROM executions
                WHERE session_id = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?;
            """, (session_id, limit, offset))
        else:
            cursor = conn.execute("""
                SELECT * FROM executions
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?;
            """, (limit, offset))

        items = []
        for r in cursor.fetchall():
            items.append({
                "id": r["id"],
                "session_id": r["session_id"],
                "command": r["command"],
                "exit_code": r["exit_code"],
                "duration_ms": r["duration_ms"],
                "raw_bytes": r["raw_bytes"],
                "raw_tokens": r["raw_tokens"],
                "compact_bytes": r["compact_bytes"],
                "compact_tokens": r["compact_tokens"],
                "savings_ratio": r["savings_ratio"],
                "status": r["status"],
                "compact_output": "",
                "error": r["error"],
                "created_at": r["created_at"],
            })
        return items
