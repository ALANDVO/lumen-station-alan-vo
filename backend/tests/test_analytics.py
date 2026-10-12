"""Tests for token analytics and part-whole invariant preservation."""

import pytest
from app.services.analytics_service import get_session_analytics, get_global_analytics
from app.services.session_guard import register_session
from app.services.sandbox_engine import execute_sandboxed_command


def test_session_zero_executions_reports_zero_savings():
    """Verify that a session with zero tool executions reports 0% savings (Issue #950)."""
    sess = register_session(platform="claude-code", quiet_mode=False)
    analytics = get_session_analytics(sess["id"])

    assert analytics["total_executions"] == 0
    assert analytics["raw_tokens"] == 0
    assert analytics["compact_tokens"] == 0
    assert analytics["saved_tokens"] == 0
    assert analytics["savings_percentage"] == 0.0


def test_global_analytics_part_whole_invariant():
    """Verify that no single session reports more saved tokens than global total (Issue #950)."""
    sess = register_session(platform="opencode", quiet_mode=False)
    execute_sandboxed_command(
        session_id=sess["id"],
        command="python3 -c \"for i in range(200): print('Log entry', i)\"",
    )

    session_stats = get_session_analytics(sess["id"])
    global_stats = get_global_analytics()

    assert session_stats["saved_tokens"] <= global_stats["saved_tokens_sum"]
    assert global_stats["part_whole_invariant_verified"] is True


def test_counterfactual_model_pricing_order():
    """Verify pricing calculations reflect relative model tier costs."""
    global_stats = get_global_analytics()
    comparisons = {m["model_name"]: m["standard_cost_usd"] for m in global_stats["models_comparison"]}

    # Opus input is more expensive than Sonnet, which is more expensive than GPT-4o
    assert comparisons["Claude 3 Opus"] >= comparisons["Claude 3.7 Sonnet"]
    assert comparisons["Claude 3.7 Sonnet"] >= comparisons["GPT-4o"]
