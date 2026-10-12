"""Authentication, authorization, and CSRF security management."""

from fastapi import Request, HTTPException, status, Depends
from typing import Optional, Dict, Any
import hmac
import hashlib
import json
import base64
import time
from app.core.config import settings

ROLES = {"viewer": 1, "operator": 2, "admin": 3}
SESSION_COOKIE_NAME = "lumen_session"
CSRF_HEADER_NAME = "X-CSRF-Token"


def generate_csrf_token(session_id: str) -> str:
    """Generate CSRF token bound to session_id."""
    message = f"{session_id}:{settings.secret_key}".encode()
    return hmac.new(settings.secret_key.encode(), message, hashlib.sha256).hexdigest()


def verify_csrf_token(session_id: str, token: str) -> bool:
    """Verify CSRF token authenticity."""
    expected = generate_csrf_token(session_id)
    return hmac.compare_digest(expected, token)


def create_session_payload(email: str, role: str) -> str:
    """Create signed session cookie payload."""
    payload = {
        "email": email,
        "role": role,
        "iat": int(time.time()),
        "exp": int(time.time()) + 86400,
    }
    raw = json.dumps(payload, separators=(",", ":")).encode()
    b64_payload = base64.urlsafe_b64encode(raw).decode()
    signature = hmac.new(settings.secret_key.encode(), b64_payload.encode(), hashlib.sha256).hexdigest()
    return f"{b64_payload}.{signature}"


def decode_session_payload(cookie_value: str) -> Optional[Dict[str, Any]]:
    """Decode and verify signed session payload."""
    try:
        parts = cookie_value.split(".")
        if len(parts) != 2:
            return None
        b64_payload, signature = parts
        expected_sig = hmac.new(settings.secret_key.encode(), b64_payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected_sig, signature):
            return None
        payload_bytes = base64.urlsafe_b64decode(b64_payload.encode())
        payload = json.loads(payload_bytes.decode())
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None


def get_current_user(request: Request) -> Dict[str, Any]:
    """Retrieve current user from session cookie or demo mode."""
    # Check session cookie
    cookie_val = request.cookies.get(SESSION_COOKIE_NAME)
    if cookie_val:
        user = decode_session_payload(cookie_val)
        if user:
            return user

    # Authorization header fallback
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]
        user = decode_session_payload(token)
        if user:
            return user

    # Local demo mode fallback
    if settings.demo_mode and not settings.oidc_enabled:
        return {
            "email": "demo-operator@lumen.local",
            "role": "operator",
            "is_demo": True,
        }

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Please log in via Keycloak OIDC.",
    )


def require_role(min_role: str):
    """Dependency enforcing role-based access control."""
    def role_checker(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        user_role = user.get("role", "viewer")
        user_level = ROLES.get(user_role, 0)
        required_level = ROLES.get(min_role, 99)
        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Requires '{min_role}' role, but current user has '{user_role}'.",
            )
        return user
    return role_checker


def verify_csrf_write(request: Request, user: Dict[str, Any] = Depends(get_current_user)):
    """Validate CSRF token on mutating requests using session cookies."""
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        if user.get("is_demo"):
            return
        csrf_header = request.headers.get(CSRF_HEADER_NAME)
        session_cookie = request.cookies.get(SESSION_COOKIE_NAME)
        if not session_cookie or not csrf_header or not verify_csrf_token(session_cookie, csrf_header):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF validation failed. Missing or invalid X-CSRF-Token.",
            )
