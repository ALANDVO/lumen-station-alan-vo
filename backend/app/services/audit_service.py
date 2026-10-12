"""Transactional audit logging service."""

import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List
from app.core.database import get_db


def log_audit_event(
    user_email: str,
    action: str,
    resource_type: str,
    resource_id: str,
    details: Dict[str, Any],
) -> str:
    """Record a persistent audit log event."""
    log_id = str(uuid.uuid4())
    now_iso = datetime.now(timezone.utc).isoformat()
    details_str = json.dumps(details, separators=(",", ":"))

    with get_db() as conn:
        conn.execute("""
            INSERT INTO audit_logs (id, user_email, action, resource_type, resource_id, details_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?);
        """, (log_id, user_email, action, resource_type, resource_id, details_str, now_iso))

    return log_id


def list_audit_logs(limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    """List recent audit logs in descending chronological order."""
    with get_db() as conn:
        cursor = conn.execute("""
            SELECT id, user_email, action, resource_type, resource_id, details_json, created_at
            FROM audit_logs
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?;
        """, (limit, offset))

        logs = []
        for r in cursor.fetchall():
            try:
                parsed_details = json.loads(r["details_json"])
            except Exception:
                parsed_details = {}
            logs.append({
                "id": r["id"],
                "user_email": r["user_email"],
                "action": r["action"],
                "resource_type": r["resource_type"],
                "resource_id": r["resource_id"],
                "details": parsed_details,
                "created_at": r["created_at"],
            })
        return logs
