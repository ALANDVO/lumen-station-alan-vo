"""Tests for LLM adapter, error redaction, and offline fallbacks."""

import pytest
from app.services.llm_client import (
    generate_offline_advisory,
    redact_sensitive_error,
    request_advisory_explanation,
)
from app.core.config import settings


def test_offline_fallback_when_no_api_key():
    """Verify deterministic offline advisory response when LLM_API_KEY is empty."""
    record = {
        "id": "rec-123",
        "command": "npm test",
        "exit_code": 0,
        "raw_tokens": 1000,
        "compact_tokens": 50,
        "savings_ratio": 0.95,
        "compact_output": "All 12 tests passed",
    }

    resp = generate_offline_advisory(record, focus="summary")
    assert resp["is_advisory"] is True
    assert resp["provider"] == "offline-deterministic"
    assert "Context reduction" in resp["explanation"]
    assert resp["grounding_record_id"] == "rec-123"


def test_error_redaction_removes_api_key():
    """Verify sensitive key redaction without hardcoding token patterns."""
    # Generate synthetic key at runtime with repeated zeroes
    synthetic_key = "synthetic_key_" + ("0" * 32)
    orig_key = settings.llm_api_key
    try:
        settings.llm_api_key = synthetic_key
        err = f"Connection error to remote endpoint with header key {synthetic_key}"
        sanitized = redact_sensitive_error(err)
        assert synthetic_key not in sanitized
        assert "[REDACTED_API_KEY]" in sanitized
    finally:
        settings.llm_api_key = orig_key


@pytest.mark.asyncio
async def test_request_advisory_explanation_offline():
    """Verify async advisory endpoint falls back cleanly to offline heuristic."""
    orig_key = settings.llm_api_key
    try:
        settings.llm_api_key = ""
        record = {
            "id": "rec-456",
            "command": "pytest",
            "exit_code": 1,
            "raw_tokens": 500,
            "compact_tokens": 100,
            "savings_ratio": 0.8,
            "compact_output": "1 failed, 4 passed",
        }
        res = await request_advisory_explanation(record, focus="failure_cause")
        assert res["provider"] == "offline-deterministic"
        assert res["grounding_record_id"] == "rec-456"
        assert "Focus failure_cause" in res["explanation"]
    finally:
        settings.llm_api_key = orig_key
