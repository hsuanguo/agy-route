"""Install/uninstall orchestrator.

Delegates target-specific operations to target subclasses (ClaudeTarget,
OpenCodeTarget, etc.) polymorphically.
"""
from __future__ import annotations

from agy_route.targets import (
    TargetInstallResult,
    TargetUninstallResult,
    all_targets,
    get as get_target,
)

NAMESPACE = "agy-route"
SKILL_BUNDLES = ("agy-web-search", "agy-research")


def install(
    target_name: str,
    *,
    skill_only: bool = False,
    hook_only: bool = False,
    dry_run: bool = False,
    skills: tuple[str, ...] = SKILL_BUNDLES,
) -> TargetInstallResult:
    target = get_target(target_name)
    return target.install_target(
        skill_only=skill_only,
        hook_only=hook_only,
        dry_run=dry_run,
        skills=skills,
        namespace=NAMESPACE,
    )


def uninstall(target_name: str) -> TargetUninstallResult:
    target = get_target(target_name)
    return target.uninstall_target(skills=SKILL_BUNDLES, namespace=NAMESPACE)


def uninstall_all() -> dict[str, TargetUninstallResult]:
    out: dict[str, TargetUninstallResult] = {}
    for t in all_targets():
        out[t.name] = t.uninstall_target(skills=SKILL_BUNDLES, namespace=NAMESPACE)
    return out
