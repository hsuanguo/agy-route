"""Install/uninstall orchestrator.

Dispatches by target:

- **claude** target (skills + JSON hook config): merge the hook
  into `~/.claude/settings.json` and drop SKILL.md files into
  `~/.claude/skills/<name>/SKILL.md`.

- **opencode** target: drop SKILL.md into `~/.claude/skills/<name>/`
  (opencode auto-loads that path), drop the JS plugin into
  `~/.config/opencode/plugins/agy-route.js` (auto-loaded), and drop
  command markdowns into `~/.config/opencode/commands/`.
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Iterable

from agy_route.targets import Target, all_targets, get as get_target


NAMESPACE = "agy-route"
SKILL_BUNDLES = ("agy-web-search", "agy-route-research")


# --- Resource helpers --------------------------------------------------------


def _packaged_text(rel: str) -> str:
    return (
        resources.files("agy_route.install_data")
        .joinpath(rel)
        .read_text()
    )


def _packaged_bytes(rel: str) -> bytes:
    return (
        resources.files("agy_route.install_data")
        .joinpath(rel)
        .read_bytes()
    )


def _packaged_skill_md(name: str) -> Path:
    """Return a temp file path containing the bundled SKILL.md body."""
    file_map = {
        "agy-web-search": "skill.md",
        "agy-route-research": "skill-research.md",
    }
    if name not in file_map:
        raise KeyError(f"unknown skill {name!r}; supported: {sorted(file_map)}")
    text = _packaged_text(file_map[name])
    fd, tmp_name = tempfile.mkstemp(prefix=f"agy-route-{name}-", suffix=".md")
    with os.fdopen(fd, "w") as fh:
        fh.write(text)
    return Path(tmp_name)


def _packaged_hook_config() -> dict:
    return json.loads(_packaged_text("hooks.json"))


def _packaged_plugin_js() -> Path:
    """Returns a temp path containing the bundled opencode plugin JS."""
    data = _packaged_bytes("opencode-plugin/agy-route.js")
    fd, tmp_name = tempfile.mkstemp(prefix="agy-route-plugin-", suffix=".js")
    with os.fdopen(fd, "wb") as fh:
        fh.write(data)
    return Path(tmp_name)


def _packaged_commands() -> list[tuple[str, Path]]:
    """Return [(basename, temp_path), ...] for every shipped opencode command."""
    bundle = resources.files("agy_route.install_data").joinpath("opencode-commands")
    out: list[tuple[str, Path]] = []
    if not bundle.is_dir():
        return out
    for entry in bundle.iterdir():
        if entry.name.endswith(".md"):
            fd, tmp_name = tempfile.mkstemp(prefix=f"agy-route-{entry.name[:-3]}-", suffix=".md")
            with os.fdopen(fd, "wb") as fh:
                fh.write(entry.read_bytes())
            out.append((entry.name, Path(tmp_name)))
    return out


# --- Result type ------------------------------------------------------------


@dataclass
class InstallResult:
    target: str
    skill_installed: bool
    skill_path: str | None
    hook_installed: bool
    plugin_installed: bool
    commands_installed: list[str]
    skill_changed: bool
    hook_changed: bool
    plugin_changed: bool
    message: str = ""


# --- Per-target dispatch ----------------------------------------------------


def install(
    target_name: str,
    *,
    skill_only: bool = False,
    hook_only: bool = False,
    dry_run: bool = False,
    skills: tuple[str, ...] = SKILL_BUNDLES,
) -> InstallResult:
    target = get_target(target_name)
    if not target.is_present():
        return InstallResult(
            target=target_name,
            skill_installed=False,
            skill_path=None,
            hook_installed=False,
            plugin_installed=False,
            commands_installed=[],
            skill_changed=False,
            hook_changed=False,
            plugin_changed=False,
            message=f"target {target_name!r} not present on this host",
        )

    skill_paths, skill_changed_any = [], False
    hook_installed, hook_changed = False, False
    plugin_installed, plugin_changed = False, False
    commands_installed: list[str] = []

    if not hook_only:
        for skill_name in skills:
            src_skill = _packaged_skill_md(skill_name)
            try:
                existing = (
                    target.home / ".claude" / "skills" / skill_name / "SKILL.md"
                )
                same_content = (
                    existing.is_file()
                    and existing.read_text() == src_skill.read_text()
                )
                if not dry_run:
                    dst = target.install_skill(src_skill, skill_name=skill_name)
                    skill_paths.append(str(dst))
                    if not same_content:
                        skill_changed_any = True
                else:
                    skill_changed_any = skill_changed_any or not same_content
                    skill_paths.append(str(existing))
            finally:
                try:
                    src_skill.unlink()
                except OSError:
                    pass

    if not skill_only:
        if target.name == "claude":
            hook_config = _packaged_hook_config()
            if not dry_run:
                target.install_hook(hook_config, namespace=NAMESPACE)
                hook_changed = True
            hook_installed = True
        elif target.name == "opencode":
            # opencode target: drop plugin JS + command markdowns.
            src_plugin = _packaged_plugin_js()
            try:
                existing_plugin = (
                    target.config_dir / "plugins" / "agy-route.js"
                )
                same_content = (
                    existing_plugin.is_file()
                    and existing_plugin.read_bytes() == src_plugin.read_bytes()
                )
                if not dry_run:
                    dst = target.install_plugin(src_plugin)
                    plugin_installed = True
                    if not same_content:
                        plugin_changed = True
                else:
                    plugin_installed = True
                    plugin_changed = not same_content
            finally:
                try:
                    src_plugin.unlink()
                except OSError:
                    pass

            if not dry_run:
                cmd_sources = _packaged_commands()
                try:
                    written = target.install_commands(cmd_sources)
                    commands_installed = [str(p) for p in written]
                finally:
                    for _, p in cmd_sources:
                        try:
                            p.unlink()
                        except OSError:
                            pass

    return InstallResult(
        target=target_name,
        skill_installed=bool(skill_paths),
        skill_path="; ".join(skill_paths) if skill_paths else None,
        hook_installed=hook_installed,
        plugin_installed=plugin_installed,
        commands_installed=commands_installed,
        skill_changed=skill_changed_any,
        hook_changed=hook_changed,
        plugin_changed=plugin_changed,
    )


def uninstall(target_name: str) -> tuple[bool, bool]:
    """Returns (skill_removed_count, hook_or_plugin_removed)."""
    target = get_target(target_name)
    skill_removed_count = sum(
        bool(target.uninstall_skill(skill_name=name))
        for name in SKILL_BUNDLES
    )
    secondary_removed = target.uninstall_hook(namespace=NAMESPACE)
    return bool(skill_removed_count), secondary_removed


def uninstall_all() -> dict[str, tuple[bool, bool]]:
    out: dict[str, tuple[bool, bool]] = {}
    for t in all_targets():
        out[t.name] = uninstall(t.name)
    return out
