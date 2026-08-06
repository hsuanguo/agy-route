"""Target registry."""
from __future__ import annotations

from typing import Iterable

from agy_route.targets.base import Target, TargetInstallResult, TargetUninstallResult
from agy_route.targets.claude import ClaudeTarget
from agy_route.targets.opencode import OpenCodeTarget

_REGISTRY: dict[str, type[Target]] = {
    "claude": ClaudeTarget,
    "opencode": OpenCodeTarget,
}


def get(name: str) -> Target:
    cls = _REGISTRY.get(name)
    if cls is None:
        raise KeyError(
            f"unknown target {name!r}; supported: {sorted(_REGISTRY)}"
        )
    return cls()


def all_targets() -> Iterable[Target]:
    return [cls() for cls in _REGISTRY.values()]


__all__ = ["TargetInstallResult", "TargetUninstallResult", "get", "all_targets"]