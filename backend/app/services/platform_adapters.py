"""Platform-specific hook definitions and adapter generation for AI coding agents."""

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
from app.core.config import settings
from app.core.database import get_db


PLATFORM_SPECS: Dict[str, Dict[str, Any]] = {
    "claude-code": {
        "display_name": "Claude Code",
        "config_path": ".claude/settings.json",
        "hook_type": "pretooluse",
        "supports_pkce": True,
        "supports_quiet_mode": True,
        "parent_death_guard": True,
        "default_timeout_seconds": 120,
        "issues_addressed": ["#911", "#967", "#947", "#982", "#950"],
    },
    "codex-cli": {
        "display_name": "Codex CLI",
        "config_path": ".codex/config.toml",
        "hook_type": "pretooluse",
        "supports_pkce": False,
        "supports_quiet_mode": True,
        "parent_death_guard": True,
        "default_timeout_seconds": 120,
        "issues_addressed": ["#982"],
    },
    "opencode": {
        "display_name": "OpenCode V2",
        "config_path": ".opencode/config.json",
        "hook_type": "mcp",
        "supports_pkce": True,
        "supports_quiet_mode": True,
        "parent_death_guard": True,
        "default_timeout_seconds": 120,
        "issues_addressed": ["#1187"],
    },
    "antigravity": {
        "display_name": "Antigravity",
        "config_path": ".antigravity/hooks.json",
        "hook_type": "pretooluse",
        "supports_pkce": True,
        "supports_quiet_mode": True,
        "parent_death_guard": True,
        "default_timeout_seconds": 120,
        "issues_addressed": ["#982"],
    },
    "pi": {
        "display_name": "Pi Interactive",
        "config_path": ".pi/config.json",
        "hook_type": "mcp",
        "supports_pkce": False,
        "supports_quiet_mode": True,
        "parent_death_guard": True,
        "default_timeout_seconds": 300,
        "issues_addressed": ["#959", "#982"],
    },
    "gemini-cli": {
        "display_name": "Gemini CLI",
        "config_path": ".gemini/settings.json",
        "hook_type": "pretooluse",
        "supports_pkce": True,
        "supports_quiet_mode": True,
        "parent_death_guard": True,
        "default_timeout_seconds": 120,
        "issues_addressed": [],
    },
    "vscode-copilot": {
        "display_name": "VS Code Copilot",
        "config_path": ".vscode/settings.json",
        "hook_type": "mcp",
        "supports_pkce": True,
        "supports_quiet_mode": True,
        "parent_death_guard": False,
        "default_timeout_seconds": 120,
        "issues_addressed": [],
    },
    "zed": {
        "display_name": "Zed Editor",
        "config_path": ".zed/settings.json",
        "hook_type": "mcp",
        "supports_pkce": True,
        "supports_quiet_mode": True,
        "parent_death_guard": False,
        "default_timeout_seconds": 120,
        "issues_addressed": [],
    },
}


def get_platform_spec(platform: str) -> Dict[str, Any]:
    """Get platform specification with defaults for unknown platforms."""
    return PLATFORM_SPECS.get(platform, {
        "display_name": platform.replace("-", " ").title(),
        "config_path": f".{platform}/config.json",
        "hook_type": "pretooluse",
        "supports_pkce": False,
        "supports_quiet_mode": True,
        "parent_death_guard": True,
        "default_timeout_seconds": 120,
        "issues_addressed": [],
    })


def generate_parent_death_guard_script(platform: str, server_url: str = "http://127.0.0.1:8000") -> str:
    """
    Generate a parent-death guard script for the target platform.
    On Windows: uses ppid polling since no SIGCHLD.
    On Linux/macOS: uses stdin EOF + ppid polling belt-and-suspenders.
    """
    spec = get_platform_spec(platform)
    timeout = spec["default_timeout_seconds"]
    now_iso = datetime.now(timezone.utc).isoformat()
    issues = ", ".join(spec["issues_addressed"]) or "general orphan prevention"

    # Use string template to avoid f-string conflicts with bash $ variables
    template = '''#!/usr/bin/env bash
# Lumen Station Parent-Death Guard for {display_name}
# Auto-generated: {now_iso}
# Issues addressed: {issues}

set -euo pipefail

LUMEN_SERVER="{server_url}"
LUMEN_TIMEOUT={timeout}
LUMEN_PLATFORM="{platform}"

# Parent PID to monitor
PARENT_PID=${{PPID:-$$}}

# Function to check if parent is alive
is_parent_alive() {{
    local ppid=$1
    if [[ $ppid -le 1 ]]; then
        return 1
    fi
    kill -0 "$ppid" 2>/dev/null
}}

# Function to register session with Lumen Station
register_session() {{
    local session_id=$(uuidgen)
    local working_dir=$(pwd)
    local os_name=$(uname -s | tr '[:upper:]' '[:lower:]')

    curl -s -X POST "$LUMEN_SERVER/api/sessions" \
        -H "Content-Type: application/json" \
        -d "$(jq -n \
            --arg id "$session_id" \
            --arg platform "$LUMEN_PLATFORM" \
            --arg wd "$working_dir" \
            --arg os "$os_name" \
            --argjson quiet false \
            '{{id: $id, platform: $platform, working_dir: $wd, os_name: $os, quiet_mode: $quiet}}')" \
        >/dev/null 2>&1 || true

    echo "$session_id"
}}

# Function to execute command through Lumen Station sandbox
execute_sandboxed() {{
    local session_id=$1
    local command=$2
    local timeout_sec=${{3:-$LUMEN_TIMEOUT}}

    curl -s -X POST "$LUMEN_SERVER/api/sandbox/execute" \
        -H "Content-Type: application/json" \
        -d "$(jq -n \
            --arg sid "$session_id" \
            --arg cmd "$command" \
            --argjson timeout "$timeout_sec" \
            '{{session_id: $sid, command: $cmd, timeout_seconds: $timeout}}')" \
        2>/dev/null || echo '{{"error": "sandbox request failed"}}'
}}

# Main guard loop - runs in background
parent_death_watchdog() {{
    local session_id=$1
    local check_interval=15

    while is_parent_alive "$PARENT_PID"; do
        sleep $check_interval
    done

    # Parent died - clean up
    echo "[Lumen Station] Parent process $PARENT_PID terminated. Cleaning up session $session_id..." >&2
    exit 0
}}

# If sourced, just export functions; if executed, run guard
if [[ "${{BASH_SOURCE[0]}}" == "${{0}}" ]]; then
    SESSION_ID=$(register_session)
    echo "[Lumen Station] Session registered: $SESSION_ID" >&2
    parent_death_watchdog "$SESSION_ID" &
    WATCHDOG_PID=$!

    # Wait for stdin EOF (when parent closes pipe)
    if [[ -t 0 ]]; then
        # Interactive - wait for watchdog
        wait $WATCHDOG_PID
    else
        # Piped input - EOF triggers exit
        cat >/dev/null
        kill $WATCHDOG_PID 2>/dev/null
        wait $WATCHDOG_PID 2>/dev/null
    fi
fi
'''
    return template.format(
        display_name=spec["display_name"],
        now_iso=now_iso,
        issues=issues,
        server_url=server_url,
        timeout=timeout,
        platform=platform,
    )


def generate_claude_code_hooks(server_url: str = "http://127.0.0.1:8000", quiet_mode: bool = False) -> Dict[str, Any]:
    """Generate Claude Code hook configuration (settings.json)."""
    spec = get_platform_spec("claude-code")

    hooks_config = {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "Bash",
                    "hooks": [
                        {
                            "type": "command",
                            "command": f"curl -s -X POST {server_url}/api/sandbox/execute -H 'Content-Type: application/json' -d @- << 'EOF'\n{{\n  \"session_id\": \"$LUMEN_SESSION_ID\",\n  \"command\": \"$TOOL_INPUT_COMMAND\",\n  \"timeout_seconds\": {spec['default_timeout_seconds']}\n}}\nEOF",
                            "timeout": spec["default_timeout_seconds"] * 1000,
                        }
                    ],
                }
            ],
            "SessionStart": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": f"curl -s -X POST {server_url}/api/sessions -H 'Content-Type: application/json' -d '{{\"platform\": \"claude-code\", \"working_dir\": \"$(pwd)\", \"os_name\": \"$(uname -s | tr '[:upper:]' '[:lower:]')\", \"quiet_mode\": {str(quiet_mode).lower()}}}' | jq -r .id",
                            "timeout": 5000,
                        }
                    ],
                }
            ],
        }
    }

    if not quiet_mode:
        # Add guidance injection hook
        hooks_config["hooks"]["SessionStart"][0]["hooks"].append({
            "type": "command",
            "command": f"curl -s -X POST {server_url}/api/sessions/guidance -H 'Content-Type: application/json' -d '{{\"session_id\": \"$LUMEN_SESSION_ID\", \"session_mode\": \"default\"}}' | jq -r .injected_block",
            "timeout": 5000,
        })

    return hooks_config


def generate_opencode_v2_mcp_config(server_url: str = "http://127.0.0.1:8000") -> Dict[str, Any]:
    """Generate OpenCode V2 MCP server configuration."""
    return {
        "mcpServers": {
            "lumen-station": {
                "command": "npx",
                "args": ["-y", "supergateway", "--stdio", f"{server_url}/mcp"],
                "env": {
                    "LUMEN_STATION_URL": server_url,
                },
            }
        }
    }


def generate_pi_mcp_config(server_url: str = "http://127.0.0.1:8000") -> Dict[str, Any]:
    """Generate Pi Interactive MCP configuration with abortable execution."""
    return {
        "mcpServers": {
            "lumen-station": {
                "command": "node",
                "args": ["-e", f"""
const {{ StdioServerTransport }} = require('@modelcontextprotocol/sdk/server/stdio.js');
const {{ MCP_SERVER }} = require('@mksglu/context-mode/build/adapters/pi/mcp-bridge.js');

const transport = new StdioServerTransport();
const server = MCP_SERVER;

// Handle abort signals for Pi (issue #959)
let abortController = new AbortController();
process.stdin.on('end', () => abortController.abort());
process.stdin.on('close', () => abortController.abort());

// Parent death polling
const ppid = process.ppid;
const pollInterval = setInterval(() => {{
    try {{ process.kill(ppid, 0); }} catch {{ process.exit(0); }}
}}, 15000).unref();

server.connect(transport).catch(console.error);
"""],
                "env": {
                    "LUMEN_STATION_URL": server_url,
                    "LUMEN_TIMEOUT": "300",
                },
            }
        }
    }


def generate_antigravity_hooks(server_url: str = "http://127.0.0.1:8000", quiet_mode: bool = False) -> Dict[str, Any]:
    """Generate Antigravity hook configuration."""
    spec = get_platform_spec("antigravity")

    return {
        "hooks": {
            "pre_tool_use": [
                {
                    "matcher": "shell",
                    "command": f"curl -s -X POST {server_url}/api/sandbox/execute -H 'Content-Type: application/json' -d '{{\"session_id\": \"$SESSION_ID\", \"command\": \"$COMMAND\", \"timeout_seconds\": {spec['default_timeout_seconds']}}}'",
                }
            ],
            "session_start": [
                {
                    "command": f"curl -s -X POST {server_url}/api/sessions -H 'Content-Type: application/json' -d '{{\"platform\": \"antigravity\", \"working_dir\": \"$PWD\", \"os_name\": \"$(uname -s | tr '[:upper:]' '[:lower:]')\", \"quiet_mode\": {str(quiet_mode).lower()}}}' | jq -r .id",
                }
            ],
        }
    }


def generate_codex_cli_config(server_url: str = "http://127.0.0.1:8000", quiet_mode: bool = False) -> str:
    """Generate Codex CLI TOML configuration."""
    spec = get_platform_spec("codex-cli")
    return f"""# Lumen Station hook configuration for Codex CLI
# Auto-generated: {datetime.now(timezone.utc).isoformat()}

[hooks]
pre_tool_use = [
    {{ matcher = "bash", command = "curl -s -X POST {server_url}/api/sandbox/execute -H 'Content-Type: application/json' -d '{{\"session_id\": \"$SESSION_ID\", \"command\": \"$COMMAND\", \"timeout_seconds\": {spec['default_timeout_seconds']}}}'" }},
]

session_start = [
    {{ command = "curl -s -X POST {server_url}/api/sessions -H 'Content-Type: application/json' -d '{{\"platform\": \"codex-cli\", \"working_dir\": \"$PWD\", \"os_name\": \"$(uname -s | tr '[:upper:]' '[:lower:]')\", \"quiet_mode\": {str(quiet_mode).lower()}}}' | jq -r .id" }},
]

[parent_death_guard]
enabled = true
check_interval_seconds = 15
"""


def generate_gemini_cli_config(server_url: str = "http://127.0.0.1:8000", quiet_mode: bool = False) -> Dict[str, Any]:
    """Generate Gemini CLI configuration."""
    spec = get_platform_spec("gemini-cli")
    config = {
        "hooks": {
            "preToolUse": [
                {
                    "matcher": "run_shell_command",
                    "command": f"curl -s -X POST {server_url}/api/sandbox/execute -H 'Content-Type: application/json' -d '{{\"session_id\": \"$SESSION_ID\", \"command\": \"$COMMAND\", \"timeout_seconds\": {spec['default_timeout_seconds']}}}'",
                }
            ],
            "sessionStart": [
                {
                    "command": f"curl -s -X POST {server_url}/api/sessions -H 'Content-Type: application/json' -d '{{\"platform\": \"gemini-cli\", \"working_dir\": \"$PWD\", \"os_name\": \"$(uname -s | tr '[:upper:]' '[:lower:]')\", \"quiet_mode\": {str(quiet_mode).lower()}}}' | jq -r .id",
                }
            ],
        }
    }
    if not quiet_mode:
        config["hooks"]["sessionStart"][0]["command"] += f" && curl -s -X POST {server_url}/api/sessions/guidance -H 'Content-Type: application/json' -d '{{\"session_id\": \"$SESSION_ID\", \"session_mode\": \"default\"}}' | jq -r .injected_block"
    return config


def generate_vscode_copilot_mcp(server_url: str = "http://127.0.0.1:8000") -> Dict[str, Any]:
    """Generate VS Code Copilot MCP configuration."""
    return {
        "mcp": {
            "servers": {
                "lumen-station": {
                    "type": "stdio",
                    "command": "npx",
                    "args": ["-y", "supergateway", "--stdio", f"{server_url}/mcp"],
                }
            }
        }
    }


def generate_zed_mcp(server_url: str = "http://127.0.0.1:8000") -> Dict[str, Any]:
    """Generate Zed Editor MCP configuration."""
    return {
        "mcp_servers": {
            "lumen-station": {
                "command": "npx",
                "args": ["-y", "supergateway", "--stdio", f"{server_url}/mcp"],
            }
        }
    }


def generate_platform_adapter(platform: str, server_url: str = "http://127.0.0.1:8000", quiet_mode: bool = False) -> Dict[str, Any]:
    """
    Generate complete platform adapter configuration including hooks, MCP config,
    and parent-death guard script.
    """
    spec = get_platform_spec(platform)

    result = {
        "platform": platform,
        "display_name": spec["display_name"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "config_path": spec["config_path"],
        "hook_type": spec["hook_type"],
        "supports_quiet_mode": spec["supports_quiet_mode"],
        "parent_death_guard_included": spec["parent_death_guard"],
        "issues_addressed": spec["issues_addressed"],
        "configuration": None,
        "parent_death_guard_script": None,
    }

    # Generate platform-specific configuration
    if platform == "claude-code":
        result["configuration"] = generate_claude_code_hooks(server_url, quiet_mode)
    elif platform == "opencode":
        result["configuration"] = generate_opencode_v2_mcp_config(server_url)
    elif platform == "pi":
        result["configuration"] = generate_pi_mcp_config(server_url)
    elif platform == "antigravity":
        result["configuration"] = generate_antigravity_hooks(server_url, quiet_mode)
    elif platform == "codex-cli":
        result["configuration"] = generate_codex_cli_config(server_url, quiet_mode)
    elif platform == "gemini-cli":
        result["configuration"] = generate_gemini_cli_config(server_url, quiet_mode)
    elif platform == "vscode-copilot":
        result["configuration"] = generate_vscode_copilot_mcp(server_url)
    elif platform == "zed":
        result["configuration"] = generate_zed_mcp(server_url)
    else:
        result["configuration"] = {"error": f"Unknown platform: {platform}"}

    # Generate parent-death guard script if supported
    if spec["parent_death_guard"]:
        result["parent_death_guard_script"] = generate_parent_death_guard_script(platform, server_url)

    return result


def write_adapter_to_filesystem(adapter: Dict[str, Any], output_dir: str = ".") -> List[str]:
    """
    Write generated adapter configuration and scripts to filesystem.
    Returns list of written file paths.
    """
    written = []
    base_path = Path(output_dir)

    # Write main configuration
    config_path = base_path / adapter["config_path"]
    config_path.parent.mkdir(parents=True, exist_ok=True)

    config_content = adapter["configuration"]
    if isinstance(config_content, str):
        config_path.write_text(config_content)
    else:
        config_path.write_text(json.dumps(config_content, indent=2))
    written.append(str(config_path))

    # Write parent-death guard script if available
    if adapter.get("parent_death_guard_script"):
        script_path = base_path / f".lumen-station/{adapter['platform']}-parent-guard.sh"
        script_path.parent.mkdir(parents=True, exist_ok=True)
        script_path.write_text(adapter["parent_death_guard_script"])
        script_path.chmod(0o755)
        written.append(str(script_path))

    return written


def register_platform_session(
    platform: str,
    working_dir: str = ".",
    os_name: str = "linux",
    quiet_mode: bool = False,
) -> Dict[str, Any]:
    """Register a session for a specific platform and return session info with adapter config."""
    import uuid

    session_id = str(uuid.uuid4())
    now_iso = datetime.now(timezone.utc).isoformat()

    with get_db() as conn:
        conn.execute("""
            INSERT INTO sessions (id, platform, working_dir, os_name, quiet_mode, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?);
        """, (session_id, platform, working_dir, os_name, 1 if quiet_mode else 0, now_iso, now_iso))

    adapter = generate_platform_adapter(platform, quiet_mode=quiet_mode)

    return {
        "session_id": session_id,
        "platform": platform,
        "working_dir": working_dir,
        "os_name": os_name,
        "quiet_mode": quiet_mode,
        "adapter": adapter,
        "created_at": now_iso,
    }


def list_supported_platforms() -> List[Dict[str, Any]]:
    """List all supported platforms with their capabilities."""
    return [
        {
            "platform": platform,
            "display_name": spec["display_name"],
            "hook_type": spec["hook_type"],
            "supports_quiet_mode": spec["supports_quiet_mode"],
            "parent_death_guard": spec["parent_death_guard"],
            "default_timeout_seconds": spec["default_timeout_seconds"],
            "issues_addressed": spec["issues_addressed"],
        }
        for platform, spec in PLATFORM_SPECS.items()
    ]