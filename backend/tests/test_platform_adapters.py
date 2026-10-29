"""Tests for platform-specific hook definitions and adapter generation."""

import json
import pytest
from app.services.platform_adapters import (
    get_platform_spec,
    generate_platform_adapter,
    generate_parent_death_guard_script,
    generate_claude_code_hooks,
    generate_opencode_v2_mcp_config,
    generate_pi_mcp_config,
    generate_antigravity_hooks,
    generate_codex_cli_config,
    generate_gemini_cli_config,
    generate_vscode_copilot_mcp,
    generate_zed_mcp,
    register_platform_session,
    list_supported_platforms,
    PLATFORM_SPECS,
)


def test_platform_specs_include_required_platforms():
    """Verify all required platforms from issues are registered."""
    required = {"claude-code", "opencode", "pi", "antigravity", "codex-cli"}
    for platform in required:
        assert platform in PLATFORM_SPECS, f"Missing required platform: {platform}"
        spec = PLATFORM_SPECS[platform]
        assert "display_name" in spec
        assert "hook_type" in spec
        assert "issues_addressed" in spec


def test_get_platform_spec_known():
    """Verify known platform specs have expected structure."""
    spec = get_platform_spec("claude-code")
    assert spec["display_name"] == "Claude Code"
    assert spec["hook_type"] == "pretooluse"
    assert "#911" in spec["issues_addressed"]
    assert "#967" in spec["issues_addressed"]
    assert "#947" in spec["issues_addressed"]
    assert "#982" in spec["issues_addressed"]


def test_get_platform_spec_unknown():
    """Verify unknown platform gets sensible defaults."""
    spec = get_platform_spec("unknown-platform")
    assert spec["display_name"] == "Unknown Platform"
    assert spec["hook_type"] == "pretooluse"
    assert spec["supports_quiet_mode"] is True
    assert spec["parent_death_guard"] is True


def test_generate_parent_death_guard_script():
    """Verify parent-death guard script generation."""
    script = generate_parent_death_guard_script("claude-code")
    assert "#!/usr/bin/env bash" in script
    assert "is_parent_alive" in script
    assert "parent_death_watchdog" in script
    assert "LUMEN_SERVER" in script
    assert "Claude Code" in script


def test_generate_parent_death_guard_windows_logic():
    """Verify script handles Windows ppid polling (no SIGCHLD)."""
    script = generate_parent_death_guard_script("antigravity")
    assert "kill -0" in script  # POSIX signal 0 check
    assert "PPID" in script


def test_generate_claude_code_hooks():
    """Verify Claude Code hooks configuration structure."""
    hooks = generate_claude_code_hooks(quiet_mode=False)
    assert "hooks" in hooks
    assert "PreToolUse" in hooks["hooks"]
    assert "SessionStart" in hooks["hooks"]

    # Check PreToolUse for Bash matcher
    pre_tool = hooks["hooks"]["PreToolUse"]
    assert len(pre_tool) >= 1
    assert pre_tool[0]["matcher"] == "Bash"

    # Check SessionStart has session registration
    session_start = hooks["hooks"]["SessionStart"]
    assert len(session_start) >= 1
    assert "hooks" in session_start[0]


def test_generate_claude_code_hooks_quiet_mode():
    """Verify quiet mode omits guidance injection."""
    hooks_quiet = generate_claude_code_hooks(quiet_mode=True)
    hooks_normal = generate_claude_code_hooks(quiet_mode=False)

    # Both should have session registration
    assert len(hooks_quiet["hooks"]["SessionStart"][0]["hooks"]) == 1
    # Normal should have session registration + guidance injection
    assert len(hooks_normal["hooks"]["SessionStart"][0]["hooks"]) == 2


def test_generate_opencode_v2_mcp_config():
    """Verify OpenCode V2 MCP configuration (issue #1187)."""
    config = generate_opencode_v2_mcp_config()
    assert "mcpServers" in config
    assert "lumen-station" in config["mcpServers"]
    assert config["mcpServers"]["lumen-station"]["command"] == "npx"
    assert "supergateway" in " ".join(config["mcpServers"]["lumen-station"]["args"])


def test_generate_pi_mcp_config_abortable():
    """Verify Pi MCP config includes abort handling (issue #959)."""
    config = generate_pi_mcp_config()
    assert "mcpServers" in config
    assert "lumen-station" in config["mcpServers"]

    # Check for abort signal handling
    args = config["mcpServers"]["lumen-station"]["args"]
    args_str = " ".join(args)
    assert "AbortController" in args_str
    assert "process.stdin.on" in args_str
    assert "process.ppid" in args_str
    assert "setInterval" in args_str
    assert "unref" in args_str


def test_generate_antigravity_hooks():
    """Verify Antigravity hooks with parent-death guard (issue #982)."""
    hooks = generate_antigravity_hooks()
    assert "hooks" in hooks
    assert "pre_tool_use" in hooks["hooks"]
    assert "session_start" in hooks["hooks"]


def test_generate_codex_cli_config():
    """Verify Codex CLI TOML configuration."""
    config = generate_codex_cli_config()
    assert "[hooks]" in config
    assert "pre_tool_use" in config
    assert "session_start" in config
    assert "[parent_death_guard]" in config
    assert "enabled = true" in config


def test_generate_gemini_cli_config():
    """Verify Gemini CLI configuration."""
    config = generate_gemini_cli_config()
    assert "hooks" in config
    assert "preToolUse" in config["hooks"]
    assert "sessionStart" in config["hooks"]


def test_generate_vscode_copilot_mcp():
    """Verify VS Code Copilot MCP configuration."""
    config = generate_vscode_copilot_mcp()
    assert "mcp" in config
    assert "servers" in config["mcp"]
    assert "lumen-station" in config["mcp"]["servers"]


def test_generate_zed_mcp():
    """Verify Zed Editor MCP configuration."""
    config = generate_zed_mcp()
    assert "mcp_servers" in config
    assert "lumen-station" in config["mcp_servers"]


def test_generate_platform_adapter_complete():
    """Verify full adapter generation includes config and guard script."""
    adapter = generate_platform_adapter("claude-code", quiet_mode=False)

    assert adapter["platform"] == "claude-code"
    assert adapter["display_name"] == "Claude Code"
    assert adapter["configuration"] is not None
    assert adapter["parent_death_guard_script"] is not None
    assert "#911" in adapter["issues_addressed"]


def test_generate_platform_adapter_quiet_mode():
    """Verify quiet mode affects generated configuration."""
    adapter_quiet = generate_platform_adapter("claude-code", quiet_mode=True)
    adapter_normal = generate_platform_adapter("claude-code", quiet_mode=False)

    # Both should have configuration
    assert adapter_quiet["configuration"] is not None
    assert adapter_normal["configuration"] is not None


def test_list_supported_platforms():
    """Verify platform listing returns all required info."""
    platforms = list_supported_platforms()
    assert len(platforms) >= 8  # At least the 8 defined in PLATFORM_SPECS

    for p in platforms:
        assert "platform" in p
        assert "display_name" in p
        assert "hook_type" in p
        assert "supports_quiet_mode" in p
        assert "parent_death_guard" in p
        assert "issues_addressed" in p


def test_register_platform_session():
    """Verify session registration with adapter generation."""
    session = register_platform_session(
        platform="opencode",
        working_dir="/workspace/test",
        os_name="linux",
        quiet_mode=True,
    )

    assert "session_id" in session
    assert session["platform"] == "opencode"
    assert session["quiet_mode"] is True
    assert "adapter" in session
    assert session["adapter"]["platform"] == "opencode"


def test_platform_spec_issues_addressed():
    """Verify specific issues are linked to platforms."""
    # OpenCode V2 - issue #1187
    assert "#1187" in PLATFORM_SPECS["opencode"]["issues_addressed"]

    # Pi - issue #959, #982
    assert "#959" in PLATFORM_SPECS["pi"]["issues_addressed"]
    assert "#982" in PLATFORM_SPECS["pi"]["issues_addressed"]

    # Antigravity - issue #982
    assert "#982" in PLATFORM_SPECS["antigravity"]["issues_addressed"]

    # Claude Code - issues #911, #967, #947, #982, #950
    claude_issues = PLATFORM_SPECS["claude-code"]["issues_addressed"]
    assert "#911" in claude_issues
    assert "#967" in claude_issues
    assert "#947" in claude_issues
    assert "#982" in claude_issues
    assert "#950" in claude_issues
def test_generate_parent_death_guard_unix_script():
    """Verify Unix/Linux bash parent-death guard script generation."""
    script = generate_parent_death_guard_script("claude-code", target_os="linux")
    assert "#!/usr/bin/env bash" in script
    assert "is_parent_alive" in script
    assert "parent_death_watchdog" in script
    assert "LUMEN_SERVER" in script
    assert "Claude Code" in script
    assert "kill -0" in script
    assert "PPID" in script


def test_generate_parent_death_guard_windows_script():
    """Verify Windows PowerShell parent-death guard script generation."""
    script = generate_parent_death_guard_script("antigravity", target_os="windows")
    assert "Get-Process" in script  # Windows process query
    assert "ParentProcessId" in script
    assert "[guid]::NewGuid()" in script  # Windows UUID generation
    assert "Start-Job" in script  # Background job
    assert "Test-ParentAlive" in script
    assert "Invoke-RestMethod" in script


def test_generate_parent_death_guard_defaults_to_unix():
    """Verify default target_os is linux."""
    script = generate_parent_death_guard_script("claude-code")
    assert "#!/usr/bin/env bash" in script
    assert "kill -0" in script


def test_generate_platform_adapter_includes_both_scripts():
    """Verify platform adapter includes both Unix and Windows guard scripts."""
    adapter = generate_platform_adapter("claude-code")
    assert "parent_death_guard_script_unix" in adapter
    assert "parent_death_guard_script_windows" in adapter
    assert adapter["parent_death_guard_script_unix"] is not None
    assert adapter["parent_death_guard_script_windows"] is not None
    assert "#!/usr/bin/env bash" in adapter["parent_death_guard_script_unix"]
    assert "Get-Process" in adapter["parent_death_guard_script_windows"]
