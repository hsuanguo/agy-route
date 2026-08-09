from pathlib import Path

from agy_route.targets import all_targets, get
from agy_route.targets.claude import ClaudeTarget
from agy_route.targets.opencode import OpenCodeTarget


def test_target_registry():
    targets = list(all_targets())
    names = [t.name for t in targets]
    assert "claude" in names
    assert "opencode" in names

    c = get("claude")
    assert isinstance(c, ClaudeTarget)
    o = get("opencode")
    assert isinstance(o, OpenCodeTarget)


def test_claude_target_install_and_uninstall(tmp_path):
    target = ClaudeTarget(home=tmp_path)
    assert target.is_present()

    # Default install: skills + commands (no hook)
    res = target.install_target()
    assert res.skill_installed is True
    assert res.hook_installed is False
    assert len(res.commands_installed) == 2
    assert (tmp_path / ".claude" / "skills" / "agy-web-search" / "SKILL.md").is_file()
    assert (tmp_path / ".claude" / "skills" / "agy-research" / "SKILL.md").is_file()
    assert (tmp_path / ".claude" / "commands" / "agy-web-search.md").is_file()
    assert (tmp_path / ".claude" / "commands" / "agy-research.md").is_file()
    assert not (tmp_path / ".claude" / "settings.json").exists()

    # Install with hook
    res_hook = target.install_target(with_hook=True)
    assert res_hook.hook_installed is True
    assert (tmp_path / ".claude" / "settings.json").is_file()

    # Uninstall
    unres = target.uninstall_target()
    assert len(unres.skills_removed) == 2
    assert unres.hook_removed is True
    assert len(unres.commands_removed) == 2

    # Uninstall again (idempotency check)
    unres_2 = target.uninstall_target()
    assert len(unres_2.skills_removed) == 0
    assert unres_2.hook_removed is False
    assert len(unres_2.commands_removed) == 0


def test_opencode_target_install_and_uninstall(tmp_path):
    target = OpenCodeTarget(home=tmp_path)
    assert target.is_present()

    # Default install: skills + commands (no plugin)
    res = target.install_target()
    assert res.skill_installed is True
    assert res.plugin_installed is False
    assert len(res.commands_installed) == 2
    assert (tmp_path / ".claude" / "skills" / "agy-web-search" / "SKILL.md").is_file()
    assert (tmp_path / ".config" / "opencode" / "commands" / "agy-web-search.md").is_file()
    assert not (tmp_path / ".config" / "opencode" / "plugins" / "agy-route.js").exists()

    # Install with plugin
    res_plugin = target.install_target(with_hook=True)
    assert res_plugin.plugin_installed is True
    assert (tmp_path / ".config" / "opencode" / "plugins" / "agy-route.js").is_file()

    # Uninstall
    unres = target.uninstall_target()
    assert len(unres.skills_removed) == 2
    assert unres.plugin_removed is True
    assert len(unres.commands_removed) == 2


def test_claude_target_preserves_existing_settings(tmp_path):
    import json

    # Setup pre-existing ~/.claude/settings.json with custom hook and permission
    settings_file = tmp_path / ".claude" / "settings.json"
    settings_file.parent.mkdir(parents=True, exist_ok=True)
    initial_content = {
        "permissions": {
            "allow": ["Bash(git status)"]
        },
        "hooks": {
            "PreToolUse": [
                {"matcher": "Bash", "hooks": [{"type": "command", "command": "my-custom-hook"}]}
            ]
        }
    }
    settings_file.write_text(json.dumps(initial_content, indent=2))

    target = ClaudeTarget(home=tmp_path)

    # 1. Install with hook
    target.install_target(with_hook=True)

    # Verify both pre-existing entries AND agy-route entries exist
    current = json.loads(settings_file.read_text())
    assert "Bash(git status)" in current["permissions"]["allow"]
    assert "Bash(agy-route search *)" in current["permissions"]["allow"]

    pretooluse_matchers = [entry["matcher"] for entry in current["hooks"]["PreToolUse"]]
    assert "Bash" in pretooluse_matchers
    assert "WebSearch" in pretooluse_matchers

    # 2. Uninstall
    target.uninstall_target()

    # Verify pre-existing entries remain intact, while agy-route entries are stripped
    after_uninstall = json.loads(settings_file.read_text())
    assert "Bash(git status)" in after_uninstall["permissions"]["allow"]
    assert "Bash(agy-route search *)" not in after_uninstall["permissions"]["allow"]

    remaining_matchers = [entry["matcher"] for entry in after_uninstall["hooks"]["PreToolUse"]]
    assert "Bash" in remaining_matchers
    assert "WebSearch" not in remaining_matchers

