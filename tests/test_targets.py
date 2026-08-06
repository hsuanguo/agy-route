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

    res = target.install_target()
    assert res.skill_installed is True
    assert res.hook_installed is True
    assert len(res.commands_installed) == 2

    # Verify files created
    assert (tmp_path / ".claude" / "skills" / "agy-web-search" / "SKILL.md").is_file()
    assert (tmp_path / ".claude" / "skills" / "agy-route-research" / "SKILL.md").is_file()
    assert (tmp_path / ".claude" / "commands" / "agy-search.md").is_file()
    assert (tmp_path / ".claude" / "commands" / "agy-research.md").is_file()
    assert (tmp_path / ".claude" / "settings.json").is_file()

    # Uninstall
    skills_removed, hook_removed = target.uninstall_target()
    assert skills_removed is True
    assert hook_removed is True

    # Uninstall again (idempotency check)
    skills_removed_2, hook_removed_2 = target.uninstall_target()
    assert skills_removed_2 is False
    assert hook_removed_2 is False


def test_opencode_target_install_and_uninstall(tmp_path):
    target = OpenCodeTarget(home=tmp_path)
    assert target.is_present()

    res = target.install_target()
    assert res.skill_installed is True
    assert res.plugin_installed is True
    assert len(res.commands_installed) == 2

    # Verify files created
    assert (tmp_path / ".claude" / "skills" / "agy-web-search" / "SKILL.md").is_file()
    assert (tmp_path / ".config" / "opencode" / "plugins" / "agy-route.js").is_file()
    assert (tmp_path / ".config" / "opencode" / "commands" / "agy-search.md").is_file()

    # Uninstall
    skills_removed, plugin_removed = target.uninstall_target()
    assert skills_removed is True
    assert plugin_removed is True
