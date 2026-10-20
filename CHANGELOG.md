# Changelog

## 1.1.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.0.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

All notable changes to Lumen Station will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-10-12

### Added
- Core tool execution sandboxing engine bounding verbose terminal output, tests, diffs, and linters with up to 98% context token reduction.
- SQLite FTS5 search indexing service for persisted execution chunks with chunk size bounds to prevent content bloat.
- Injection-safe session guidance formatter avoiding auto-mode security classifier false positives (`Auto-Mode Bypass` triggers).
- Hard wall-clock execution watchdog and process lifecycle manager with process tree termination and parent-death polling guards.
- Invariant-preserving token analytics computing per-session and global token savings, counterfactual LLM cost comparisons, and part-whole consistency.
- Multi-provider LLM adapter supporting OpenAI-compatible, Anthropic messages, Gemini generateContent, and Ollama endpoints with secure key handling.
- Keycloak OIDC authentication flow with PKCE, state/nonce validation, upstream SAML identity brokering support, and localhost-only demo mode.
- React + TypeScript dashboard with tool execution sandboxing, live folding preview, FTS5 chunk query, guidance generator, and analytics views.
- Offline reproducible evaluation benchmark suite (`backend.app.evaluation.evaluate_context_savings`).
