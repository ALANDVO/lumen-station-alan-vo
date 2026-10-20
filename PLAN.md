# Product development plan

Each round completes one feature or repair. Future items are planned, not implemented claims.

## Current round

multi-platform-agent-adapters

## Roadmap

### context-sandboxing-engine — Context Window Optimization and Tool Sandboxing Engine

Status: done

Acceptance:
- Intercepts verbose tool and terminal outputs and folds lines above threshold, achieving up to 98% context token reduction.
- Enforces hard wall-clock execution timeouts to prevent hung processes across agent platforms.
- Indexes output chunks into SQLite FTS5 for precision on-demand retrieval.
- Provides interactive frontend sandbox runner and live token savings visualization.

Implementation: `backend/app/main.py`, `backend/app/services/sandbox_engine.py`, `backend/app/services/search_index.py`, `backend/app/services/lifecycle_manager.py`, `backend/app/api/routes_sandbox.py`, `frontend/src/components/ExecutionSandbox.tsx`

Tests: `backend/tests/test_sandbox.py`, `backend/tests/test_search_fts.py`, `backend/tests/test_lifecycle.py`, `backend/tests/test_api_workflows.py`, `frontend/src/__tests__/dashboard.test.tsx`

### safe-session-guidance — Classifier-Safe Advisory Session Guidance and Multi-Platform Registry

Status: done

Acceptance:
- Formats non-imperative advisory tool guidance blocks to avoid auto-mode bypass security denials.
- Provides quiet-mode toggle to eliminate injected transcript blocks for security-conscious users.

Implementation: `backend/app/services/session_guard.py`, `backend/app/api/routes_sessions.py`, `frontend/src/components/SessionGuidance.tsx`

Tests: `backend/tests/test_session_guard.py`

### invariant-token-analytics — Invariant-Preserving Token Economics and Model Pricing Comparison

Status: done

Acceptance:
- Strictly verifies that per-session kept out tokens never exceed global totals.
- Reports zero savings for sessions with zero tool executions.
- Calculates counterfactual cost comparisons across Claude, GPT, and Gemini model tiers.

Implementation: `backend/app/services/analytics_service.py`, `backend/app/api/routes_analytics.py`, `frontend/src/components/AnalyticsDashboard.tsx`

Tests: `backend/tests/test_analytics.py`, `backend/tests/test_api_workflows.py`

### multi-platform-agent-adapters — Multi-Platform Agent Hooks and Process Watchdog Adapters

Status: in_progress

Acceptance:
- Provides platform-specific hook definitions for OpenCode V2, Pi, Claude Code, and Antigravity.
- Enforces parent-death polling guards to prevent orphaned background processes on Windows and Linux.

Implementation: `backend/app/services/platform_adapters.py`

Tests: `backend/tests/test_platform_adapters.py`

