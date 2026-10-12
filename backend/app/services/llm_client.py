"""Multi-provider LLM adapter for opt-in advisory analysis."""

import httpx
from typing import Dict, Any, Optional
from app.core.config import settings

PROVIDER_DEFAULTS = {
    "openai-compatible": "https://api.openai.com/v1",
    "anthropic": "https://api.anthropic.com/v1",
    "gemini": "https://generativelanguage.googleapis.com/v1beta",
    "ollama": "http://127.0.0.1:11434",
}


def redact_sensitive_error(message: str) -> str:
    """Sanitize error messages to prevent leaking credential tokens."""
    if not message:
        return "Unknown error"
    sanitized = message
    if settings.llm_api_key:
        sanitized = sanitized.replace(settings.llm_api_key, "[REDACTED_API_KEY]")
    return sanitized


def generate_offline_advisory(
    execution_record: Dict[str, Any],
    focus: str = "summary",
) -> Dict[str, Any]:
    """
    Generate deterministic offline heuristic explanation without invoking external LLMs.
    Guarantees full offline functionality when no API key is provided.
    """
    cmd = execution_record.get("command", "")
    exit_code = execution_record.get("exit_code")
    raw_tokens = execution_record.get("raw_tokens", 0)
    compact_tokens = execution_record.get("compact_tokens", 0)
    savings = round(execution_record.get("savings_ratio", 0.0) * 100.0, 1)

    analysis_points = [
        f"Command executed: `{cmd}` with exit code {exit_code}.",
        f"Context reduction: Saved {raw_tokens - compact_tokens} tokens ({savings}% reduction).",
    ]

    if exit_code != 0:
        analysis_points.append("Execution ended with non-zero exit code. Review head/tail error lines in compact preview.")
    else:
        analysis_points.append("Execution completed successfully.")

    if focus == "failure_cause" and exit_code != 0:
        analysis_points.append("Focus failure_cause: Inspect compiler/test failure logs indexed in SQLite FTS5 store.")
    elif focus == "diff_summary":
        analysis_points.append("Focus diff_summary: Git diff or structural changes folded to prevent context bloat.")

    explanation = " [Deterministic Offline Advisory] " + " ".join(analysis_points)

    return {
        "execution_id": execution_record["id"],
        "provider": "offline-deterministic",
        "model": "lumen-heuristic-engine",
        "is_advisory": True,
        "grounding_record_id": execution_record["id"],
        "explanation": explanation,
        "raw_prompt_tokens": 0,
        "raw_completion_tokens": 0,
    }


async def request_advisory_explanation(
    execution_record: Dict[str, Any],
    focus: str = "summary",
) -> Dict[str, Any]:
    """
    Generate an opt-in advisory explanation grounded in execution record.
    Uses operator-configured LLM provider with strict error redaction.
    """
    api_key = settings.llm_api_key
    provider = settings.llm_provider.lower()
    model = settings.llm_model

    # If key is absent, use deterministic offline fallback
    if not api_key and provider != "ollama":
        return generate_offline_advisory(execution_record, focus)

    base_url = settings.llm_base_url or PROVIDER_DEFAULTS.get(provider, "https://api.openai.com/v1")
    prompt = (
        f"You are Lumen Station's advisory assistant. Ground your response strictly on the tool record below.\n"
        f"Focus: {focus}\n"
        f"Command: {execution_record.get('command')}\n"
        f"Exit Code: {execution_record.get('exit_code')}\n"
        f"Summary Output Preview:\n{execution_record.get('compact_output', '')[:1500]}\n\n"
        f"Provide a concise 2-3 sentence advisory diagnostic."
    )

    timeout = httpx.Timeout(15.0, connect=5.0)

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            if provider == "openai-compatible":
                url = f"{base_url.rstrip('/')}/chat/completions"
                headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                body = {
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 200,
                }
                resp = await client.post(url, json=body, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                text = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})
                p_tokens = usage.get("prompt_tokens", 0)
                c_tokens = usage.get("completion_tokens", 0)

            elif provider == "anthropic":
                url = f"{base_url.rstrip('/')}/messages"
                headers = {
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                }
                body = {
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 200,
                }
                resp = await client.post(url, json=body, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                text = data["content"][0]["text"]
                usage = data.get("usage", {})
                p_tokens = usage.get("input_tokens", 0)
                c_tokens = usage.get("output_tokens", 0)

            elif provider == "gemini":
                url = f"{base_url.rstrip('/')}/models/{model}:generateContent"
                headers = {"x-goog-api-key": api_key, "Content-Type": "application/json"}
                body = {
                    "contents": [{"parts": [{"text": prompt}]}],
                }
                resp = await client.post(url, json=body, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                p_tokens = 0
                c_tokens = 0

            elif provider == "ollama":
                url = f"{base_url.rstrip('/')}/api/chat"
                body = {
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                }
                resp = await client.post(url, json=body)
                resp.raise_for_status()
                data = resp.json()
                text = data["message"]["content"]
                p_tokens = data.get("prompt_eval_count", 0)
                c_tokens = data.get("eval_count", 0)

            else:
                return generate_offline_advisory(execution_record, focus)

            return {
                "execution_id": execution_record["id"],
                "provider": provider,
                "model": model,
                "is_advisory": True,
                "grounding_record_id": execution_record["id"],
                "explanation": text.strip(),
                "raw_prompt_tokens": p_tokens,
                "raw_completion_tokens": c_tokens,
            }

    except Exception as exc:
        redacted = redact_sensitive_error(str(exc))
        # Never fabricate success on provider error
        return {
            "execution_id": execution_record["id"],
            "provider": provider,
            "model": model,
            "is_advisory": True,
            "grounding_record_id": execution_record["id"],
            "explanation": f"Provider error: Unable to generate LLM explanation ({redacted}). Offline summary: {generate_offline_advisory(execution_record, focus)['explanation']}",
            "raw_prompt_tokens": 0,
            "raw_completion_tokens": 0,
        }
