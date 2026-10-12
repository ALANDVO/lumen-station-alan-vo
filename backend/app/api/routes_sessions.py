"""Session registry and safe prompt guidance generation endpoints."""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import Dict, Any, List

from app.core.security import require_role, verify_csrf_write
from app.models.schemas import (
    SessionCreate,
    SessionResponse,
    GuidanceRequest,
    GuidanceResponse,
    SessionAnalytics,
)
from app.services.session_guard import register_session, generate_session_guidance, list_sessions
from app.services.analytics_service import get_session_analytics
from app.services.audit_service import log_audit_event

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("", response_model=SessionResponse, dependencies=[Depends(verify_csrf_write)])
def create_session(
    req: SessionCreate,
    user: Dict[str, Any] = Depends(require_role("operator")),
) -> Dict[str, Any]:
    """Register a new coding agent session."""
    session = register_session(
        platform=req.platform,
        working_dir=req.working_dir,
        os_name=req.os_name,
        quiet_mode=req.quiet_mode,
    )

    log_audit_event(
        user_email=user.get("email", "unknown"),
        action="CREATE_SESSION",
        resource_type="session",
        resource_id=session["id"],
        details={"platform": req.platform, "quiet_mode": req.quiet_mode},
    )

    return session


@router.get("", response_model=List[Dict[str, Any]])
def get_sessions(
    limit: int = 50,
    user: Dict[str, Any] = Depends(require_role("viewer")),
) -> List[Dict[str, Any]]:
    """List recent agent sessions."""
    return list_sessions(limit=limit)


@router.post("/guidance", response_model=GuidanceResponse)
def get_session_prompt_guidance(
    req: GuidanceRequest,
    user: Dict[str, Any] = Depends(require_role("viewer")),
) -> Dict[str, Any]:
    """
    Generate an injection-safe advisory prompt guidance block for an agent session.
    Avoids aggressive imperative authority tags to prevent auto-mode classifier denials.
    """
    return generate_session_guidance(
        session_id=req.session_id,
        session_mode=req.session_mode or "default",
    )


@router.get("/{session_id}/analytics", response_model=SessionAnalytics)
def get_single_session_analytics(
    session_id: str,
    user: Dict[str, Any] = Depends(require_role("viewer")),
) -> Dict[str, Any]:
    """
    Retrieve token savings analytics for a single session.
    Guarantees that a session with zero tool executions reports 0% savings.
    """
    return get_session_analytics(session_id)
