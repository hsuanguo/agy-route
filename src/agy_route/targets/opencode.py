"""opencode target — drop skills + plugin + commands into the user's opencode config dir."""
from __future__ import annotations

import shutil
from pathlib import Path

from agy_route.core.resources import read_package_resource
from agy_route.specs import COMMAND_SPECS
from agy_route.targets.base import Target, TargetInstallResult, TargetUninstallResult


class OpenCodeTarget(Target):
    name = "opencode"
    description = "opencode — ~/.config/opencode/{skills,plugins,commands}/ (auto-loaded)"

    def __init__(self, home: Path | None = None) -> None:
        self.home = (home or Path.home()).expanduser()
        self.config_dir = self.home / ".config" / "opencode"
        self.skill_subdir = ".claude/skills"
        self.hook_config_path = self.config_dir / "plugins"
        self.hook_config_format = "json"

    def is_present(self) -> bool:
        return self.home.is_dir()

    def install_target(
        self,
        *,
        with_hook: bool = False,
        skill_only: bool = False,
        hook_only: bool = False,
        dry_run: bool = False,
        skills: tuple[str, ...] = ("agy-web-search", "agy-research"),
        namespace: str = "agy-route",
    ) -> TargetInstallResult:
        if not self.is_present():
            return TargetInstallResult(
                target=self.name,
                skill_installed=False,
                skill_path=None,
                hook_installed=False,
                plugin_installed=False,
                message=f"target {self.name!r} not present on this host",
            )

        skill_paths: list[str] = []
        skill_changed_any = False
        plugin_installed = False
        plugin_changed = False
        commands_installed: list[str] = []

        install_skills = not hook_only
        install_commands = not hook_only and not skill_only
        install_plugin = hook_only or with_hook

        if install_skills:
            for skill_name in skills:
                content = read_package_resource("skills", skill_name, "SKILL.md")
                dst_dir = self.home / ".claude" / "skills" / skill_name
                dst = dst_dir / "SKILL.md"
                same_content = dst.is_file() and dst.read_text() == content
                if not dry_run:
                    dst_dir.mkdir(parents=True, exist_ok=True)
                    if not same_content:
                        dst.write_text(content)
                skill_paths.append(str(dst))
                skill_changed_any = skill_changed_any or not same_content

        if install_commands:
            dst_cmd_dir = self.config_dir / "commands"
            if not dry_run:
                dst_cmd_dir.mkdir(parents=True, exist_ok=True)

            for spec in COMMAND_SPECS:
                dst_cmd = dst_cmd_dir / f"{spec.name}.md"
                content = spec.render_opencode()
                same_content = dst_cmd.is_file() and dst_cmd.read_text() == content
                if not dry_run:
                    if not same_content:
                        dst_cmd.write_text(content)
                commands_installed.append(str(dst_cmd))

        if install_plugin:
            # Install plugin JS
            plugin_text = read_package_resource("plugins", "opencode", "agy-route.js")
            plugin_bytes = plugin_text.encode("utf-8")
            dst_plugin_dir = self.config_dir / "plugins"
            dst_plugin = dst_plugin_dir / "agy-route.js"
            plugin_same = (
                dst_plugin.is_file() and dst_plugin.read_bytes() == plugin_bytes
            )
            plugin_installed = True
            if not dry_run:
                dst_plugin_dir.mkdir(parents=True, exist_ok=True)
                if not plugin_same:
                    dst_plugin.write_bytes(plugin_bytes)
                plugin_changed = not plugin_same
            else:
                plugin_changed = not plugin_same

        return TargetInstallResult(
            target=self.name,
            skill_installed=bool(skill_paths),
            skill_path="; ".join(skill_paths) if skill_paths else None,
            hook_installed=False,
            plugin_installed=plugin_installed,
            commands_installed=commands_installed,
            skill_paths=skill_paths,
            plugin_path=str(dst_plugin) if plugin_installed else None,
            skill_changed=skill_changed_any,
            plugin_changed=plugin_changed,
        )

    def uninstall_target(
        self,
        *,
        skills: tuple[str, ...] = ("agy-web-search", "agy-research"),
        namespace: str = "agy-route",
    ) -> TargetUninstallResult:
        skills_removed: list[str] = []
        for skill_name in skills:
            dst_dir = self.home / ".claude" / "skills" / skill_name
            if dst_dir.is_dir():
                shutil.rmtree(dst_dir)
                skills_removed.append(str(dst_dir))

        plugin = self.config_dir / "plugins" / "agy-route.js"
        cmds_dir = self.config_dir / "commands"
        plugin_removed = False
        commands_removed: list[str] = []

        if plugin.is_file():
            plugin.unlink()
            plugin_removed = True

        if cmds_dir.is_dir():
            for f in cmds_dir.glob("agy-*.md"):
                commands_removed.append(str(f))
                f.unlink()
            try:
                cmds_dir.rmdir()
            except OSError:
                pass

        return TargetUninstallResult(
            target=self.name,
            skills_removed=skills_removed,
            hook_removed=False,
            plugin_removed=plugin_removed,
            commands_removed=commands_removed,
        )
