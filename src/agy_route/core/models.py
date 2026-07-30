"""Model auto-resolution and cache management for agy-route."""
from __future__ import annotations

import os
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

_MODEL_CACHE = Path(
    os.environ.get("AGY_ROUTE_MODEL_CACHE")
    or (Path.home() / ".cache" / "agy-route-models")
)
_MODEL_CACHE_TTL_SEC = 3600


@dataclass
class ResolvedModel:
    name: str
    from_cache: bool


def resolve_model_name(agy_models_output: str, type_name: str) -> Optional[str]:
    """Pick the best Flash model from the `agy models` listing.

    Preference order:
      - Flash (High)   — preferred for web search (cheap, fast, grounded)
      - Flash (Medium) — fallback
      - Flash (Low)    — last resort
      - any line containing 'flash' (case insensitive)
    """
    lines = [ln.strip() for ln in agy_models_output.splitlines() if ln.strip()]
    rank = (
        ("high", 3),
        ("medium", 2),
        ("low", 1),
    )
    best: tuple[int, str] | None = None
    for line in lines:
        ll = line.lower()
        if "flash" not in ll:
            continue
        # match "flash-high", "flash (high)", "flash-high-..."
        for tag, score in rank:
            if re.search(rf"flash[ _-]?{tag}", ll):
                if best is None or score > best[0]:
                    best = (score, line)
                break
    if best is not None:
        return best[1]
    # last resort
    for line in lines:
        if "flash" in line.lower():
            return line
    return None


def read_cache(type_name: str) -> Optional[str]:
    """Read a cached model name if cache exists and is unexpired."""
    if not _MODEL_CACHE.is_file():
        return None
    try:
        age = time.time() - _MODEL_CACHE.stat().st_mtime
        if age >= _MODEL_CACHE_TTL_SEC:
            return None
    except OSError:
        return None
    try:
        for ln in _MODEL_CACHE.read_text().splitlines():
            parts = ln.split("\t", 2)
            if len(parts) == 3 and parts[1] == type_name:
                return parts[2]
    except (ValueError, OSError):
        return None
    return None


def write_cache(type_name: str, name: str) -> None:
    """Write model resolution entry into local cache file."""
    try:
        _MODEL_CACHE.parent.mkdir(parents=True, exist_ok=True)
        existing_lines: list[str] = []
        if _MODEL_CACHE.is_file():
            for ln in _MODEL_CACHE.read_text().splitlines():
                parts = ln.split("\t", 2)
                if len(parts) == 3 and parts[1] != type_name:
                    existing_lines.append(ln)
        existing_lines.append(f"{int(time.time())}\t{type_name}\t{name}")
        _MODEL_CACHE.write_text("\n".join(existing_lines) + "\n")
    except OSError:
        pass  # cache is best-effort


def resolve_model(type_name: str, override: Optional[str] = None) -> ResolvedModel:
    """Resolve model name using override, local cache, or `agy models` process."""
    if override:
        return ResolvedModel(name=override, from_cache=False)
    cached = read_cache(type_name)
    if cached:
        return ResolvedModel(name=cached, from_cache=True)
    try:
        agy_models = subprocess.run(
            ["agy", "models"],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout
    except (FileNotFoundError, subprocess.SubprocessError, subprocess.TimeoutExpired):
        return ResolvedModel(name="", from_cache=False)
    name = resolve_model_name(agy_models, type_name)
    if not name:
        return ResolvedModel(name="", from_cache=False)
    write_cache(type_name, name)
    return ResolvedModel(name=name, from_cache=False)
