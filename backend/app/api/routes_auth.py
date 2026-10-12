"""Authentication, OIDC authorization flow, and session endpoints."""

from fastapi import APIRouter, Request, Response, HTTPException, status, Depends
from typing import Dict, Any
import secrets
import hashlib
import base64
import httpx
from app.core.config import settings
from app.core.security import (
    get_current_user,
    create_session_payload,
    generate_csrf_token,
    SESSION_COOKIE_NAME,
)
from app.services.audit_service import log_audit_event

router = APIRouter(prefix="/api/auth", tags=["auth"])

# In-memory PKCE and state store for pending OIDC handshakes
_OIDC_STATES: Dict[str, Dict[str, str]] = {}


@router.get("/me")
def get_user_profile(user: Dict[str, Any] = Depends(get_current_user), request: Request = None) -> Dict[str, Any]:
    """Retrieve current authenticated profile and CSRF token."""
    session_cookie = request.cookies.get(SESSION_COOKIE_NAME, "demo-session")
    csrf_token = generate_csrf_token(session_cookie)
    return {
        "email": user.get("email"),
        "role": user.get("role", "viewer"),
        "is_demo": user.get("is_demo", False),
        "csrf_token": csrf_token,
    }


@router.get("/login")
def login_oidc(response: Response) -> Dict[str, Any]:
    """
    Initiate Keycloak OIDC authorization-code flow with PKCE and state protection.
    """
    if not settings.oidc_enabled or not settings.oidc_issuer_url:
        if settings.demo_mode:
            return {
                "message": "OIDC is disabled. Running in local demo mode.",
                "auth_url": "/api/auth/demo-login",
                "mode": "demo",
            }
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OIDC provider is not configured and demo mode is disabled.",
        )

    # Generate PKCE verifier and challenge
    code_verifier = secrets.token_urlsafe(64)
    code_challenge = base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest()).decode().rstrip("=")
    state = secrets.token_urlsafe(32)

    _OIDC_STATES[state] = {
        "code_verifier": code_verifier,
        "created_at": str(secrets.randbelow(1000000)),
    }

    auth_endpoint = f"{settings.oidc_issuer_url.rstrip('/')}/protocol/openid-connect/auth"
    redirect_url = (
        f"{auth_endpoint}?"
        f"response_type=code&"
        f"client_id={settings.oidc_client_id}&"
        f"redirect_uri={settings.oidc_redirect_uri}&"
        f"scope=openid%20profile%20email&"
        f"state={state}&"
        f"code_challenge={code_challenge}&"
        f"code_challenge_method=S256"
    )

    return {
        "auth_url": redirect_url,
        "state": state,
        "mode": "oidc",
    }


@router.get("/callback")
async def callback_oidc(code: str, state: str, response: Response) -> Dict[str, Any]:
    """
    Handle OIDC authorization code exchange, state check, and issue HttpOnly session cookie.
    """
    state_data = _OIDC_STATES.pop(state, None)
    if not state_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OIDC state parameter.",
        )

    token_endpoint = f"{settings.oidc_issuer_url.rstrip('/')}/protocol/openid-connect/token"
    payload = {
        "grant_type": "authorization_code",
        "client_id": settings.oidc_client_id,
        "client_secret": settings.oidc_client_secret,
        "code": code,
        "redirect_uri": settings.oidc_redirect_uri,
        "code_verifier": state_data["code_verifier"],
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            token_resp = await client.post(token_endpoint, data=payload)
            token_resp.raise_for_status()
            token_data = token_resp.json()

            # Userinfo request
            userinfo_endpoint = f"{settings.oidc_issuer_url.rstrip('/')}/protocol/openid-connect/userinfo"
            user_resp = await client.get(
                userinfo_endpoint,
                headers={"Authorization": f"Bearer {token_data['access_token']}"},
            )
            user_resp.raise_for_status()
            user_info = user_resp.json()

            email = user_info.get("email", "unknown@lumen.local")
            roles = user_info.get("realm_access", {}).get("roles", [])
            role = "viewer"
            if "admin" in roles:
                role = "admin"
            elif "operator" in roles:
                role = "operator"

            session_val = create_session_payload(email, role)
            response.set_cookie(
                key=SESSION_COOKIE_NAME,
                value=session_val,
                httponly=True,
                samesite="lax",
                secure=settings.environment.lower() == "production",
                max_age=86400,
            )

            log_audit_event(email, "LOGIN_OIDC", "session", email, {"role": role})

            return {"message": "Authenticated successfully", "email": email, "role": role}

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"OIDC token exchange failed: {exc}",
        )


@router.post("/demo-login")
def demo_login(response: Response, role: str = "operator") -> Dict[str, Any]:
    """
    Explicit local development demo login. Refused in production.
    """
    if settings.environment.lower() in {"production", "prod"} or not settings.demo_mode:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo login is strictly prohibited in production.",
        )

    valid_role = role if role in {"viewer", "operator", "admin"} else "operator"
    email = f"demo-{valid_role}@lumen.local"
    session_val = create_session_payload(email, valid_role)

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_val,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=86400,
    )

    log_audit_event(email, "LOGIN_DEMO", "session", email, {"role": valid_role})

    return {
        "message": "Demo login successful",
        "email": email,
        "role": valid_role,
        "is_demo": True,
    }


@router.post("/logout")
def logout(response: Response, user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, str]:
    """Clear session cookie and log event."""
    response.delete_cookie(key=SESSION_COOKIE_NAME)
    log_audit_event(user.get("email", "anonymous"), "LOGOUT", "session", user.get("email", ""), {})
    return {"message": "Logged out successfully"}
