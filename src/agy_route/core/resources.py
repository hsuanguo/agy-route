"""Resource loader for agy-route.

Safely loads bundled assets (skills, plugins, policies) from either
the installed wheel (`importlib.resources`) or local dev checkout.
"""
from __future__ import annotations

from importlib import resources
from pathlib import Path


def read_package_resource(*parts: str) -> str:
    """Read resource text, trying package resources first, then dev checkout root."""
    try:
        traversable = resources.files("agy_route")
        for part in parts:
            traversable = traversable.joinpath(part)
        if traversable.is_file():
            return traversable.read_text()
    except (FileNotFoundError, OSError, ModuleNotFoundError, TypeError):
        pass

    # Fallback to repo root (src/agy_route/core/resources.py -> 3 levels up)
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    local_file = repo_root.joinpath(*parts)
    if local_file.is_file():
        return local_file.read_text()

    raise FileNotFoundError(f"Resource {'/'.join(parts)!r} not found")
