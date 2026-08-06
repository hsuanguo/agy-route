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
    assert (tmp_path / ".claude" / "skills" / "agy-research" / "SKILL.md").is_file()
    assert (tmp_path / ".claude" / "commands" / "agy-web-search.md").is_file()
    assert (tmp_path / ".claude" / "commands" / "agy-research.md").is_file()
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

    res = target.install_target()
    assert res.skill_installed is True
    assert res.plugin_installed is True
    assert len(res.commands_installed) == 2

    # Verify files created
    assert (tmp_path / ".claude" / "skills" / "agy-web-search" / "SKILL.md").is_file()
    assert (tmp_path / ".config" / "opencode" / "plugins" / "agy-route.js").is_file()
    assert (tmp_path / ".config" / "opencode" / "commands" / "agy-web-search.md").is_file()

    # Uninstall
    unres = target.uninstall_target()
    assert len(unres.skills_removed) == 2
    assert unres.plugin_removed is True
    assert len(unres.commands_removed) == 2
