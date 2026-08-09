"""Tests for Claude Code marketplace configuration and plugin manifests."""
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_marketplace_json_validity():
    mp_path = REPO_ROOT / ".claude-plugin" / "marketplace.json"
    assert mp_path.is_file()
    data = json.loads(mp_path.read_text())

    assert data.get("name") == "agy-route"
    assert "plugins" in data
    assert isinstance(data["plugins"], list)

    plugin_names = [p.get("name") for p in data["plugins"]]
    assert "agy-route" in plugin_names
    assert "agy-route-hook" in plugin_names

    for plugin in data["plugins"]:
        source = plugin.get("source")
        assert source, f"Plugin {plugin} missing source field"
        # source is relative to repository root
        plugin_dir = (REPO_ROOT / source).resolve()
        assert plugin_dir.is_dir(), f"Plugin directory {plugin_dir} does not exist"
        manifest_file = plugin_dir / "plugin.json"
        assert manifest_file.is_file(), f"Manifest file {manifest_file} does not exist"


def test_base_plugin_manifest():
    """Verify /plugin install agy-route manifest installs skills, commands, and permissions without PreToolUse hook."""
    base_path = REPO_ROOT / "plugins" / "claude" / "marketplace" / "base" / "plugin.json"
    assert base_path.is_file()
    data = json.loads(base_path.read_text())

    assert data.get("name") == "agy-route"
    assert "skills" in data
    assert "commands" in data
    assert "hooks" in data

    for skill_rel in data["skills"]:
        skill_path = (base_path.parent / skill_rel).resolve()
        assert skill_path.is_dir(), f"Skill directory {skill_path} does not exist"

    for cmd_rel in data["commands"]:
        cmd_path = (base_path.parent / cmd_rel).resolve()
        assert cmd_path.is_file(), f"Command file {cmd_path} does not exist"

    # Verify permissions are configured
    hooks_rel = data["hooks"]
    perm_path = (base_path.parent / hooks_rel).resolve()
    assert perm_path.is_file(), f"Permissions file {perm_path} does not exist"
    perm_data = json.loads(perm_path.read_text())
    assert "permissions" in perm_data
    assert "allow" in perm_data["permissions"]
    assert "Bash(agy-route search *)" in perm_data["permissions"]["allow"]
    assert "Bash(agy-route research *)" in perm_data["permissions"]["allow"]
    # Ensure NO PreToolUse hook in base plugin
    assert "hooks" not in perm_data


def test_hook_plugin_manifest():
    """Verify /plugin install agy-route-hook manifest configures the PreToolUse hook."""
    hook_path = REPO_ROOT / "plugins" / "claude" / "marketplace" / "hook" / "plugin.json"
    assert hook_path.is_file()
    data = json.loads(hook_path.read_text())

    assert data.get("name") == "agy-route-hook"
    assert "hooks" in data

    hooks_rel = data["hooks"]
    settings_path = (hook_path.parent / hooks_rel).resolve()
    assert settings_path.is_file(), f"Hooks settings file {settings_path} does not exist"
    settings_data = json.loads(settings_path.read_text())
    assert "hooks" in settings_data
    assert "PreToolUse" in settings_data["hooks"]
    matcher_entries = settings_data["hooks"]["PreToolUse"]
    matchers = [entry.get("matcher") for entry in matcher_entries if isinstance(entry, dict)]
    assert "WebSearch" in matchers
