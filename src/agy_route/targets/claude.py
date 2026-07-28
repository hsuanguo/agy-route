"""Claude Code target — drop skills into ~/.claude/skills/, merge hooks into ~/.claude/settings.json."""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any

from agy_route.targets.base import Target


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
    bak = path.with_suffix(path.suffix + f".bak.{int(os.path.getmtime(path))}")
    shutil.copy2(path, bak)
    return bak


class ClaudeTarget(Target):
    name = "claude"
    description = "Claude Code — ~/.claude/skills/ + ~/.claude/settings.json"
    skill_subdir = "skills"
    hook_config_format = "json"

    def __init__(self, home: Path | None = None) -> None:
        self.home = (home or Path.home()).expanduser()
        self.config_dir = self.home / ".claude"
        self.hook_config_path = self.config_dir / "settings.json"

    def is_present(self) -> bool:
        # Claude Code is "present" as long as the user's home dir is set;
        # we always create the config dir on first install.
        return self.home.is_dir()

    def install_skill(self, src_skill_md: Path, skill_name: str = "agy-web-search") -> Path:
        dst_dir = self.config_dir / self.skill_subdir / skill_name
        dst = dst_dir / "SKILL.md"
        dst_dir.mkdir(parents=True, exist_ok=True)
        if dst.is_file() and dst.read_text() == src_skill_md.read_text():
            return dst  # idempotent
        shutil.copy2(src_skill_md, dst)
        return dst

    def uninstall_skill(self, skill_name: str = "agy-web-search") -> bool:
        dst_dir = self.config_dir / self.skill_subdir / skill_name
        if not dst_dir.is_dir():
            return False
        shutil.rmtree(dst_dir)
        return True

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

    def install_hook(self, hook_config: dict, namespace: str = "agy-route") -> None:
        self.config_dir.mkdir(parents=True, exist_ok=True)
        current = _read_json(self.hook_config_path)

        # Build the new entry from the packaged hook_config (always
        # a list of dicts per Claude Code's schema).
        new_entries = []
        for raw in hook_config.get("hooks", {}).get("PreToolUse", []):
            entry = json.loads(json.dumps(raw))  # deep copy
            self._tag(entry, namespace)
            new_entries.append(entry)

        existing_hooks = current.setdefault("hooks", {})
        existing_pretooluse = existing_hooks.setdefault("PreToolUse", [])
        if not isinstance(existing_pretooluse, list):
            existing_pretooluse = []
            existing_hooks["PreToolUse"] = existing_pretooluse

        # Drop our previous entries, then append the new ones. Idempotent.
        for i in reversed(self._our_entries(existing_pretooluse, namespace)):
            del existing_pretooluse[i]
        existing_pretooluse.extend(new_entries)

        _backup(self.hook_config_path)
        _write_json(self.hook_config_path, current)

    def uninstall_hook(self, namespace: str = "agy-route") -> bool:
        if not self.hook_config_path.is_file():
            return False
        current = _read_json(self.hook_config_path)
        hooks = current.get("hooks") or {}
        pretooluse = hooks.get("PreToolUse") or []
        if not isinstance(pretooluse, list) or not self._our_entries(pretooluse, namespace):
            return False
        for i in reversed(self._our_entries(pretooluse, namespace)):
            del pretooluse[i]
        _backup(self.hook_config_path)
        _write_json(self.hook_config_path, current)
        return True