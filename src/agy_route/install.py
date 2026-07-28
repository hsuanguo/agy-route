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


def _packaged_skill_md() -> Path:
    """Path to the SKILL.md mirror shipped with the wheel."""
    text = (
        resources.files("agy_route.install_data")
        .joinpath("skill.md")
        .read_text()
    )
    # Write to a temp file so callers can pass a Path consistently.
    import tempfile

    fd, name = tempfile.mkstemp(prefix="agy-route-skill-", suffix=".md")
    import os

    with os.fdopen(fd, "w") as fh:
        fh.write(text)
    return Path(name)


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

    skill_installed = False
    skill_changed = False
    skill_path: str | None = None
    hook_installed = False
    hook_changed = False

    src_skill = _packaged_skill_md()
    try:
        if not hook_only:
            existing = target.config_dir / target.skill_subdir / "agy-web-search" / "SKILL.md"
            same_content = (
                existing.is_file()
                and existing.read_text() == src_skill.read_text()
            )
            if not dry_run:
                dst = target.install_skill(src_skill)
                skill_path = str(dst)
                skill_installed = True
                skill_changed = not same_content
            else:
                skill_installed = not same_content
                skill_changed = not same_content
                skill_path = str(existing if same_content else existing.with_suffix(".preview"))

        if not skill_only:
            hook_config = _packaged_hook_config()
            if not dry_run:
                target.install_hook(hook_config, namespace=NAMESPACE)
                hook_installed = True
                hook_changed = True  # orchestrator tracks separately
            else:
                hook_installed = True
                hook_changed = False
    finally:
        try:
            src_skill.unlink()
        except OSError:
            pass

    return InstallResult(
        target=target_name,
        skill_installed=skill_installed,
        skill_path=skill_path,
        hook_installed=hook_installed,
        skill_changed=skill_changed,
        hook_changed=hook_changed,
    )


def uninstall(target_name: str) -> tuple[bool, bool]:
    """Returns (skill_removed, hook_removed)."""
    target = get_target(target_name)
    skill_removed = target.uninstall_skill()
    hook_removed = target.uninstall_hook(namespace=NAMESPACE)
    return skill_removed, hook_removed


def uninstall_all() -> dict[str, tuple[bool, bool]]:
    """Scan every registered target; return per-target (skill_removed, hook_removed)."""
    out: dict[str, tuple[bool, bool]] = {}
    for t in all_targets():
        out[t.name] = (t.uninstall_skill(), t.uninstall_hook(namespace=NAMESPACE))
    return out