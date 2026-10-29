# Changelog

## 1.2.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.1.1 — work-in-progress checkpoint

### Added
- Cross-platform parent-death guard support for AI agent process lifecycle management:
  - Windows PowerShell parent-death guard script generation (`_generate_windows_parent_death_guard`)
  - Unix/Linux bash parent-death guard with improved uuidgen fallback
  - `target_os` parameter support in `generate_parent_death_guard_script`
- Platform adapter API endpoints at `/api/platform-adapters`:
  - `GET /api/platform-adapters` - List all supported platforms
  - `GET /api/platform-adapters/{platform}` - Get adapter configuration for platform and OS
  - `POST /api/platform-adapters/register` - Register new platform session with adapter config
- Updated `generate_platform_adapter` to return both Unix and Windows guard scripts
- Updated `write_adapter_to_filesystem` to write both `.sh` and `.ps1` scripts
- Updated `register_platform_session` to pass `os_name` as `target_os`
- Comprehensive tests for Windows and Unix parent-death guard scripts

### Changed
- `multi-platform-agent-adapters` feature marked complete with full cross-platform support
- Platform adapter configuration now includes `parent_death_guard_script_unix` and `parent_death_guard_script_windows`

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
