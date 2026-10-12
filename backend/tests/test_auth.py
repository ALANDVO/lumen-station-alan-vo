"""Tests for authentication, RBAC, and demo mode safety."""

import pytest
from fastapi import HTTPException
from app.core.config import Settings
from app.core.security import (
    create_session_payload,
    decode_session_payload,
    generate_csrf_token,
    verify_csrf_token,
)


def test_session_cookie_signature_verification():
    """Verify session cookie signing and tampering detection."""
    cookie = create_session_payload("operator@example.com", "operator")
    decoded = decode_session_payload(cookie)

    assert decoded is not None
    assert decoded["email"] == "operator@example.com"
    assert decoded["role"] == "operator"

    # Tampered cookie
    tampered = cookie[:-4] + "abcd"
    assert decode_session_payload(tampered) is None


def test_csrf_token_generation_and_verification():
    """Verify CSRF token binding to session."""
    session_id = "test-session-id-12345"
    token = generate_csrf_token(session_id)

    assert verify_csrf_token(session_id, token) is True
    assert verify_csrf_token("different-session-id", token) is False
    assert verify_csrf_token(session_id, "invalid-token-value") is False


def test_demo_mode_refusal_in_production():
    """Verify that settings startup refuses demo_mode=True in production."""
    with pytest.raises(ValueError, match="Startup refused"):
        Settings(ENVIRONMENT="production", DEMO_MODE=True)


def test_unauthenticated_request_rejected_without_demo(client):
    """Verify 401 when demo mode is turned off and no cookie is provided."""
    from app.core.config import settings
    orig_demo = settings.demo_mode
    try:
        settings.demo_mode = False
        settings.oidc_enabled = True

        response = client.get("/api/auth/me")
        assert response.status_code == 401
    finally:
        settings.demo_mode = orig_demo
        settings.oidc_enabled = False
