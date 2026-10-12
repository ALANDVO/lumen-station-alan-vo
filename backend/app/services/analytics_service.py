"""Analytics engine computing token savings with strict invariant verification."""

from typing import Dict, Any, List
from app.core.database import get_db

# Price per million input tokens (USD)
MODEL_PRICING_PER_M_TOKENS = {
    "Claude 3.7 Sonnet": 3.00,
    "Claude 3 Opus": 15.00,
    "GPT-4o": 2.50,
    "Gemini 1.5 Pro": 3.50,
}


def get_session_analytics(session_id: str) -> Dict[str, Any]:
    """
    Calculate token savings for a specific session.
    Guarantees that a session with zero executions reports 0% savings (fixing Issue #950).
    """
    with get_db() as conn:
        session_row = conn.execute("SELECT platform FROM sessions WHERE id = ?;", (session_id,)).fetchone()
        platform = session_row["platform"] if session_row else "unknown"

        row = conn.execute("""
            SELECT 
                COUNT(id) as exec_count,
                COALESCE(SUM(raw_tokens), 0) as raw_tokens,
                COALESCE(SUM(compact_tokens), 0) as compact_tokens,
                COALESCE(SUM(duration_ms), 0.0) as duration_ms
            FROM executions
            WHERE session_id = ?;
        """, (session_id,)).fetchone()

        exec_count = row["exec_count"]
        raw_tokens = row["raw_tokens"]
        compact_tokens = row["compact_tokens"]
        duration_ms = row["duration_ms"]

        if exec_count == 0 or raw_tokens == 0:
            saved_tokens = 0
            savings_pct = 0.0
        else:
            saved_tokens = max(0, raw_tokens - compact_tokens)
            savings_pct = round((saved_tokens / float(raw_tokens)) * 100.0, 2)

        return {
            "session_id": session_id,
            "platform": platform,
            "total_executions": exec_count,
            "raw_tokens": raw_tokens,
            "compact_tokens": compact_tokens,
            "saved_tokens": saved_tokens,
            "savings_percentage": savings_pct,
            "duration_total_ms": round(duration_ms, 2),
        }


def get_global_analytics() -> Dict[str, Any]:
    """
    Calculate global token savings across all sessions.
    Verifies the part-whole invariant: no single session can report more saved tokens
    than the global total.
    """
    with get_db() as conn:
        sessions_count = conn.execute("SELECT COUNT(id) FROM sessions;").fetchone()[0]

        row = conn.execute("""
            SELECT 
                COUNT(id) as exec_count,
                COALESCE(SUM(raw_tokens), 0) as raw_tokens,
                COALESCE(SUM(compact_tokens), 0) as compact_tokens
            FROM executions;
        """).fetchone()

        exec_count = row["exec_count"]
        raw_tokens = row["raw_tokens"]
        compact_tokens = row["compact_tokens"]

        if exec_count == 0 or raw_tokens == 0:
            saved_tokens_sum = 0
            overall_pct = 0.0
        else:
            saved_tokens_sum = max(0, raw_tokens - compact_tokens)
            overall_pct = round((saved_tokens_sum / float(raw_tokens)) * 100.0, 2)

        # Invariant verification (Issue #950)
        # Check max session saved tokens <= global saved tokens sum
        session_max_row = conn.execute("""
            SELECT MAX(COALESCE(session_saved, 0)) as max_saved
            FROM (
                SELECT SUM(raw_tokens - compact_tokens) as session_saved
                FROM executions
                GROUP BY session_id
            );
        """).fetchone()
        max_session_saved = session_max_row["max_saved"] or 0
        part_whole_ok = max_session_saved <= saved_tokens_sum

        # Calculate model cost comparison
        models_comparison: List[Dict[str, Any]] = []
        for model_name, rate in MODEL_PRICING_PER_M_TOKENS.items():
            standard_cost = round((raw_tokens / 1_000_000.0) * rate, 4)
            sandboxed_cost = round((compact_tokens / 1_000_000.0) * rate, 4)
            saved_cost = round(max(0.0, standard_cost - sandboxed_cost), 4)
            models_comparison.append({
                "model_name": model_name,
                "standard_cost_usd": standard_cost,
                "sandboxed_cost_usd": sandboxed_cost,
                "saved_cost_usd": saved_cost,
            })

        return {
            "total_sessions": sessions_count,
            "total_executions": exec_count,
            "raw_tokens_sum": raw_tokens,
            "compact_tokens_sum": compact_tokens,
            "saved_tokens_sum": saved_tokens_sum,
            "overall_savings_percentage": overall_pct,
            "models_comparison": models_comparison,
            "part_whole_invariant_verified": part_whole_ok,
        }
