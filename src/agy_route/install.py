"""Install/uninstall orchestrator — drops the SKILL.md + hook config into the target."""
from __future__ import annotations

import json
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Iterable

from agy_route.targets import Target, all_targets, get as get_target


NAMESPACE = "agy-route"


@dataclass
class InstallResult:
    target: str
    skill_installed: bool
    skill_path: str | None
    hook_installed: bool
    skill_changed: bool
    hook_changed: bool
    message: str = ""


def _packaged_skill_md(name: str = "agy-web-search") -> Path:
    """Path to the SKILL.md mirror shipped with the wheel.

    `name` selects the skill bundle; `agy-web-search` reads
    `install_data/skill.md`, `agy-route-research` reads
    `install_data/skill-research.md`. The names map to filenames
    inside the package.
    """
    file_map = {
        "agy-web-search": "skill.md",
        "agy-route-research": "skill-research.md",
    }
    if name not in file_map:
        raise KeyError(f"unknown skill {name!r}; supported: {sorted(file_map)}")
    text = (
        resources.files("agy_route.install_data")
        .joinpath(file_map[name])
        .read_text()
    )
    import tempfile

    fd, tmp_name = tempfile.mkstemp(prefix=f"agy-route-{name}-", suffix=".md")
    import os

    with os.fdopen(fd, "w") as fh:
        fh.write(text)
    return Path(tmp_name)


def _packaged_hook_config() -> dict:
    text = (
        resources.files("agy_route.install_data")
        .joinpath("hooks.json")
        .read_text()
    )
    return json.loads(text)


def install(
    target_name: str,
    *,
    skill_only: bool = False,
    hook_only: bool = False,
    dry_run: bool = False,
    skills: tuple[str, ...] = ("agy-web-search", "agy-route-research"),
) -> InstallResult:
    target = get_target(target_name)
    if not target.is_present():
        return InstallResult(
            target=target_name,
            skill_installed=False,
            skill_path=None,
            hook_installed=False,
            skill_changed=False,
            hook_changed=False,
            message=f"target {target_name!r} not present on this host",
        )

    skill_paths: list[str] = []
    skill_changed_any = False
    hook_installed = False
    hook_changed = False

    if not hook_only:
        for skill_name in skills:
            src_skill = _packaged_skill_md(skill_name)
            try:
                existing = (
                    target.config_dir / target.skill_subdir / skill_name / "SKILL.md"
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
                    if not same_content:
                        skill_changed_any = True
                    skill_paths.append(
                        str(existing if same_content else existing.with_suffix(".preview"))
                    )
            finally:
                try:
                    src_skill.unlink()
                except OSError:
                    pass

    if not skill_only:
        hook_config = _packaged_hook_config()
        if not dry_run:
            target.install_hook(hook_config, namespace=NAMESPACE)
            hook_installed = True
            hook_changed = True
        else:
            hook_installed = True
            hook_changed = False

    return InstallResult(
        target=target_name,
        skill_installed=bool(skill_paths),
        skill_path="; ".join(skill_paths) if skill_paths else None,
        hook_installed=hook_installed,
        skill_changed=skill_changed_any,
        hook_changed=hook_changed,
    )


def uninstall(target_name: str) -> tuple[bool, bool]:
    """Returns (skill_removed_count, hook_removed). Removes ALL agy-route skills."""
    target = get_target(target_name)
    skill_removed_count = 0
    for skill_name in ("agy-web-search", "agy-route-research"):
        if target.uninstall_skill(skill_name=skill_name):
            skill_removed_count += 1
    hook_removed = target.uninstall_hook(namespace=NAMESPACE)
    return bool(skill_removed_count), hook_removed


def uninstall_all() -> dict[str, tuple[bool, bool]]:
    """Scan every registered target; return per-target (any_skill_removed, hook_removed)."""
    out: dict[str, tuple[bool, bool]] = {}
    for t in all_targets():
        skill_removed_count = 0
        for skill_name in ("agy-web-search", "agy-route-research"):
            if t.uninstall_skill(skill_name=skill_name):
                skill_removed_count += 1
        out[t.name] = (bool(skill_removed_count), t.uninstall_hook(namespace=NAMESPACE))
    return out