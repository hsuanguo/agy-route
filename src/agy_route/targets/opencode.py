"""opencode target — drop skills + plugin + commands into the user's opencode
config dir. Opencode auto-loads everything from `~/.config/opencode/`.
"""
from __future__ import annotations

import json
import os
import shutil
from importlib import resources
from pathlib import Path
from typing import Any

from agy_route.targets.base import Target


def _read_text_from_package(rel: str) -> str:
    """Read a UTF-8 text file shipped inside the wheel via install_data."""
    return (
        resources.files("agy_route.install_data")
        .joinpath(rel)
        .read_text()
    )


def _read_bytes_from_package(rel: str) -> bytes:
    return (
        resources.files("agy_route.install_data")
        .joinpath(rel)
        .read_bytes()
    )


class OpenCodeTarget(Target):
    name = "opencode"
    description = "opencode — ~/.config/opencode/{skills,plugins,commands}/ (auto-loaded)"

    def __init__(self, home: Path | None = None) -> None:
        self.home = (home or Path.home()).expanduser()
        # opencode config layout (https://opencode.ai/docs/):
        # - skills: read from ~/.claude/skills/<n>/SKILL.md (same dir Claude Code uses!)
        #   AND from ~/.agents/skills/<n>/SKILL.md
        # - plugins: read from ~/.config/opencode/plugins/<file>.js
        # - commands: read from ~/.config/opencode/commands/<file>.md
        self.config_dir = self.home / ".config" / "opencode"
        # opencode also reads Claude's skills dir, so we use the
        # `claude` slot in the parent target classifier for skill
        # installs (so uninstall cleans the same path).
        self.skill_subdir = ".claude/skills"  # shared with Claude Code
        self.hook_config_path = self.config_dir / "plugins"
        self.hook_config_format = "json"  # unused: opencode reads files, not settings.json

    # is_present(): pretends yes so install proceeds; users without opencode
    # can still install (the JS plugin sits dormant in ~/.config/opencode/plugins
    # and Claude/Code will silently skip it on read if the dir doesn't exist).

    def is_present(self) -> bool:
        return self.home.is_dir()

    def install_skill(
        self, src_skill_md: Path, skill_name: str = "agy-web-search"
    ) -> Path:
        """opencode auto-loads skills from ~/.claude/skills/**/SKILL.md
        (see packages/opencode/src/skill/index.ts). Drop into the same
        path Claude Code uses; one install covers both."""
        dst_dir = self.home / ".claude" / "skills" / skill_name
        dst = dst_dir / "SKILL.md"
        dst_dir.mkdir(parents=True, exist_ok=True)
        if dst.is_file() and dst.read_text() == src_skill_md.read_text():
            return dst
        shutil.copy2(src_skill_md, dst)
        return dst

    def uninstall_skill(self, skill_name: str = "agy-web-search") -> bool:
        dst_dir = self.home / ".claude" / "skills" / skill_name
        if not dst_dir.is_dir():
            return False
        shutil.rmtree(dst_dir)
        return True

    # opencode target doesn't merge into a JSON config; it just drops
    # auto-loaded files into ~/.config/opencode/{plugins,commands}/.
    # install_hook() takes no JSON: we override the ABC signature via
    # aliases below. We DO need to drop the plugin JS + command markdowns.

    def install_plugin(self, src_plugin_js: Path) -> Path:
        """Drop the agy-route.js plugin into ~/.config/opencode/plugins/.
        Opencode auto-loads every .js / .ts file in that dir on startup.

        `src_plugin_js` is typically a tempfile with a suffix like
        `agy-route-plugin-XXXX.js`; we always drop it as `agy-route.js`
        regardless of the source filename.
        """
        dst_dir = self.config_dir / "plugins"
        dst = dst_dir / "agy-route.js"
        dst_dir.mkdir(parents=True, exist_ok=True)
        if dst.is_file() and dst.read_bytes() == src_plugin_js.read_bytes():
            return dst
        shutil.copy2(src_plugin_js, dst)
        return dst

    def install_commands(
        self,
        command_sources: list[tuple[str, Path]],
    ) -> list[Path]:
        """Drop command markdowns into ~/.config/opencode/commands/.

        `command_sources` is a list of (basename, source_path) tuples
        e.g. [("agy-search.md", Path(".../agy-search.md")), ...].
        Opencode auto-loads every .md file in that dir on startup.
        """
        dst_dir = self.config_dir / "commands"
        dst_dir.mkdir(parents=True, exist_ok=True)
        written: list[Path] = []
        for basename, src in command_sources:
            dst = dst_dir / basename
            shutil.copy2(src, dst)
            written.append(dst)
        return written

    def uninstall_hook(self, namespace: str = "agy-route") -> bool:
        """For opencode, the 'hook' is the JS plugin file. Remove it
        and all installed command markdowns."""
        plugin = self.config_dir / "plugins" / "agy-route.js"
        cmds_dir = self.config_dir / "commands"
        removed = False
        if plugin.is_file():
            plugin.unlink()
            removed = True
        if cmds_dir.is_dir():
            for f in cmds_dir.glob("agy-*.md"):
                f.unlink()
                removed = True
            # Clean up empty dirs we created.
            try:
                cmds_dir.rmdir()
            except OSError:
                pass  # user-added files; leave the dir
        return removed

    # ABC stubs (never called for opencode, but must exist):
    def install_hook(self, hook_config: dict, namespace: str = "agy-route") -> None:  # type: ignore[override]
        raise NotImplementedError(
            "opencode target uses install_plugin() / install_commands(); "
            "no JSON hook config to merge."
        )

    # Skill-side name clash (we override install_skill to use the right dir,
    # but keep the same default name 'agy-web-search' / 'agy-route-research').
    def _remember_subdir(self) -> str:
        # Helper used by agy_route.install to construct the destination
        # path on disk. Always the same: ~/.claude/skills/<name>/SKILL.md.
        return ".claude/skills"
