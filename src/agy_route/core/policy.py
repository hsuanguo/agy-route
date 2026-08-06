"""Policy file loader for agy-route."""
from __future__ import annotations

from agy_route.core.resources import read_package_resource

_POLICY_FILES = {
    "search": "search.md",
}


def find_policy(name: str) -> str:
    """Find and return the content of the specified policy file."""
    rel = _POLICY_FILES.get(name)
    if rel is None:
        raise FileNotFoundError(
            f"unknown type {name!r}; supported: {sorted(_POLICY_FILES)}"
        )
    try:
        return read_package_resource("config", "policies", rel)
    except FileNotFoundError as e:
        raise FileNotFoundError(
            f"policy file not found for type {name!r} (looked in config/policies/{rel})"
        ) from e
