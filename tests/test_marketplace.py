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
    assert "permissions" in data
    assert "hooks" not in data

    for skill_rel in data["skills"]:
        skill_path = (base_path.parent / skill_rel).resolve()
        assert skill_path.is_dir(), f"Skill directory {skill_path} does not exist"

    for cmd_rel in data["commands"]:
        cmd_path = (base_path.parent / cmd_rel).resolve()
        assert cmd_path.is_file(), f"Command file {cmd_path} does not exist"

    # Verify inline permissions object
    perms = data["permissions"]
    assert "allow" in perms
    assert "Bash(agy-route search *)" in perms["allow"]
    assert "Bash(agy-route research *)" in perms["allow"]


def test_hook_plugin_manifest():
    """Verify /plugin install agy-route-hook manifest configures the PreToolUse hook."""
    hook_path = REPO_ROOT / "plugins" / "claude" / "marketplace" / "hook" / "plugin.json"
    assert hook_path.is_file()
    data = json.loads(hook_path.read_text())

    assert data.get("name") == "agy-route-hook"
    assert "hooks" in data
    assert isinstance(data["hooks"], dict)

    hooks_obj = data["hooks"]
    assert "PreToolUse" in hooks_obj
    matcher_entries = hooks_obj["PreToolUse"]
    matchers = [entry.get("matcher") for entry in matcher_entries if isinstance(entry, dict)]
    assert "WebSearch" in matchers
