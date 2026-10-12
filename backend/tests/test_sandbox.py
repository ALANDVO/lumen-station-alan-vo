"""Unit tests for sandboxing engine and folding logic."""

import pytest
from app.services.sandbox_engine import fold_large_output, execute_sandboxed_command, get_execution_detail
from app.services.search_index import estimate_tokens


def test_fold_large_output_preserves_head_and_tail():
    """Verify that folding large output retains specified head and tail lines."""
    lines = [f"line_{i}\n" for i in range(1, 101)]
    raw = "".join(lines)

    compact, omitted_count, omitted_bytes = fold_large_output(
        content=raw,
        execution_id="test-exec-123",
        head_lines_count=10,
        tail_lines_count=10,
    )

    assert "line_1\n" in compact
    assert "line_10\n" in compact
    assert "line_91\n" in compact
    assert "line_100\n" in compact
    assert "Omitted 80 lines" in compact
    assert omitted_count == 80
    assert omitted_bytes > 0


def test_fold_small_output_unaltered():
    """Verify that output below the threshold is returned unaltered."""
    small = "line 1\nline 2\nline 3\n"
    compact, omitted_count, omitted_bytes = fold_large_output(
        content=small,
        execution_id="test-exec-456",
        head_lines_count=10,
        tail_lines_count=10,
    )

    assert compact == small
    assert omitted_count == 0
    assert omitted_bytes == 0


def test_estimate_tokens_deterministic():
    """Verify deterministic token estimation."""
    assert estimate_tokens("") == 0
    toks = estimate_tokens("Hello world this is a test of token counting.")
    assert toks > 0
    assert estimate_tokens("short") < estimate_tokens("a much longer sentence with many more words")


def test_execute_sandboxed_command_success():
    """Verify command execution and metrics recording."""
    result = execute_sandboxed_command(
        session_id="test-session-cmd",
        command="echo 'Lumen Station Sandbox Test'",
    )

    assert result["exit_code"] == 0
    assert result["status"] == "completed"
    assert "Lumen Station Sandbox Test" in result["raw_output"]
    assert result["raw_tokens"] > 0
    assert result["duration_ms"] >= 0.0


def test_execute_sandboxed_command_timeout_enforced():
    """Verify hard timeout budget enforcement."""
    result = execute_sandboxed_command(
        session_id="test-session-timeout",
        command="sleep 5",
        timeout_seconds=1,
    )

    assert result["status"] == "timeout"
    assert result["exit_code"] == -1
    assert "exceeded hard timeout budget" in (result["error"] or "")


def test_get_execution_detail_not_found():
    """Verify 404 behavior for unknown execution ID."""
    assert get_execution_detail("nonexistent-id-000") is None
