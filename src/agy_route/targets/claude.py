"""Claude Code target — drop skills into ~/.claude/skills/, commands into ~/.claude/commands/, merge hooks into ~/.claude/settings.json."""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

from agy_route.core.resources import read_package_resource
from agy_route.specs import COMMAND_SPECS
from agy_route.targets.base import Target, TargetInstallResult, TargetUninstallResult


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        with path.open() as fh:
            data = json.load(fh)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    tmp.replace(path)


def _backup(path: Path) -> Path | None:
    if not path.is_file():
        return None
    rand = os.urandom(4).hex()
    bak = path.with_suffix(path.suffix + f".bak.{int(os.path.getmtime(path))}.{rand}")
    shutil.copy2(path, bak)
    return bak


class ClaudeTarget(Target):
    name = "claude"
    description = "Claude Code — ~/.claude/{skills,commands}/ + ~/.claude/settings.json"
    skill_subdir = "skills"
    hook_config_format = "json"

    def __init__(self, home: Path | None = None) -> None:
        self.home = (home or Path.home()).expanduser()
        self.config_dir = self.home / ".claude"
        self.hook_config_path = self.config_dir / "settings.json"

    def is_present(self) -> bool:
        return self.home.is_dir()

    def _tag(self, entry: dict[str, Any], namespace: str) -> None:
        """Stamp our namespace on a hook entry so uninstall can find it."""
        entry.setdefault("_meta", {})["agy_route"] = namespace

    def _our_entries(self, hook_list: list[Any], namespace: str) -> list[int]:
        return [
            i
            for i, entry in enumerate(hook_list)
            if isinstance(entry, dict)
            and isinstance(entry.get("_meta"), dict)
            and entry["_meta"].get("agy_route") == namespace
        ]

    def install_skill_content(self, skill_name: str, content: str, dry_run: bool = False) -> tuple[Path, bool]:
        dst_dir = self.config_dir / self.skill_subdir / skill_name
        dst = dst_dir / "SKILL.md"
        same_content = dst.is_file() and dst.read_text() == content
        if not dry_run:
            dst_dir.mkdir(parents=True, exist_ok=True)
            if not same_content:
                dst.write_text(content)
        return dst, not same_content

    def install_target(
        self,
        *,
        skill_only: bool = False,
        hook_only: bool = False,
        dry_run: bool = False,
        skills: tuple[str, ...] = ("agy-web-search", "agy-route-research"),
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
        hook_installed = False
        hook_changed = False
        commands_installed: list[str] = []

        if not hook_only:
            for skill_name in skills:
                content = read_package_resource("skills", skill_name, "SKILL.md")
                dst, changed = self.install_skill_content(skill_name, content, dry_run=dry_run)
                skill_paths.append(str(dst))
                skill_changed_any = skill_changed_any or changed

            # Install dynamically rendered Claude slash commands
            dst_cmd_dir = self.config_dir / "commands"
            if not dry_run:
                dst_cmd_dir.mkdir(parents=True, exist_ok=True)

            for spec in COMMAND_SPECS:
                dst_cmd = dst_cmd_dir / f"{spec.name}.md"
                content = spec.render_claude()
                same_content = dst_cmd.is_file() and dst_cmd.read_text() == content
                if not dry_run:
                    if not same_content:
                        dst_cmd.write_text(content)
                commands_installed.append(str(dst_cmd))

        if not skill_only:
            hook_config_text = read_package_resource("plugins", "claude", "hooks.json")
            hook_config = json.loads(hook_config_text)
            hook_installed = True
            if not dry_run:
                self.config_dir.mkdir(parents=True, exist_ok=True)
                current = _read_json(self.hook_config_path)
                new_entries = []
                for raw in hook_config.get("hooks", {}).get("PreToolUse", []):
                    entry = json.loads(json.dumps(raw))
                    self._tag(entry, namespace)
                    new_entries.append(entry)

                existing_hooks = current.setdefault("hooks", {})
                existing_pretooluse = existing_hooks.setdefault("PreToolUse", [])
                if not isinstance(existing_pretooluse, list):
                    existing_pretooluse = []
                    existing_hooks["PreToolUse"] = existing_pretooluse

                for i in reversed(self._our_entries(existing_pretooluse, namespace)):
                    del existing_pretooluse[i]
                existing_pretooluse.extend(new_entries)

                _backup(self.hook_config_path)
                _write_json(self.hook_config_path, current)
                hook_changed = True

        return TargetInstallResult(
            target=self.name,
            skill_installed=bool(skill_paths),
            skill_path="; ".join(skill_paths) if skill_paths else None,
            hook_installed=hook_installed,
            plugin_installed=False,
            commands_installed=commands_installed,
            skill_changed=skill_changed_any,
            hook_changed=hook_changed,
        )

    def uninstall_target(
        self,
        *,
        skills: tuple[str, ...] = ("agy-web-search", "agy-route-research"),
        namespace: str = "agy-route",
    ) -> TargetUninstallResult:
        skills_removed: list[str] = []
        for skill_name in skills:
            dst_dir = self.config_dir / self.skill_subdir / skill_name
            if dst_dir.is_dir():
                shutil.rmtree(dst_dir)
                skills_removed.append(str(dst_dir))

        commands_removed: list[str] = []
        cmds_dir = self.config_dir / "commands"
        if cmds_dir.is_dir():
            for f in cmds_dir.glob("agy-*.md"):
                commands_removed.append(str(f))
                f.unlink()
            try:
                cmds_dir.rmdir()
            except OSError:
                pass

        hook_removed = False
        if self.hook_config_path.is_file():
            current = _read_json(self.hook_config_path)
            hooks = current.get("hooks") or {}
            pretooluse = hooks.get("PreToolUse") or []
            if isinstance(pretooluse, list) and self._our_entries(pretooluse, namespace):
                for i in reversed(self._our_entries(pretooluse, namespace)):
                    del pretooluse[i]
                _backup(self.hook_config_path)
                _write_json(self.hook_config_path, current)
                hook_removed = True

        return TargetUninstallResult(
            target=self.name,
            skills_removed=skills_removed,
            hook_removed=hook_removed,
            plugin_removed=False,
            commands_removed=commands_removed,
        )