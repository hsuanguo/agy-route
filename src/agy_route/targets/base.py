"""Target ABC — one implementation per agent (Claude Code, opencode, …)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Literal

HookFormat = Literal["json", "jsonc", "toml"]


class Target(ABC):
    """A target agent's settings layout (skill dir + hook config path/format).

    Concrete targets implement `install_skill`, `install_hook`,
    `uninstall_skill`, `uninstall_hook`. Each method is idempotent.

    The orchestrator (`agy_route.install`) calls into the right methods
    based on the user's `--target {claude|opencode|...}` flag.
    """

    #: Stable name used in the CLI flag (`--target claude`).
    name: str
    #: User-friendly description for `agy-route targets`.
    description: str
    #: Absolute path to the user's agent config dir (e.g. `~/.claude/`).
    config_dir: Path
    #: Subdirectory under config_dir that holds skills.
    skill_subdir: str
    #: Absolute path to the agent's hook config file (settings.json, etc).
    hook_config_path: Path
    #: Format of the hook config file (json / jsonc / toml).
    hook_config_format: HookFormat

    @abstractmethod
    def is_present(self) -> bool:
        """Whether this target's config_dir / hook_config_path is detectable on the host."""

    @abstractmethod
    def install_skill(self, src_skill_md: Path, skill_name: str = "agy-web-search") -> Path:
        """Drop the SKILL.md into the target's skill dir. Returns the install path.

        Must be idempotent: re-running with the same content is a no-op.
        """

    @abstractmethod
    def uninstall_skill(self, skill_name: str = "agy-web-search") -> bool:
        """Remove the installed skill. Returns True if anything was removed."""

    @abstractmethod
    def install_hook(self, hook_config: dict, namespace: str = "agy-route") -> None:
        """Merge our hook entry into the target's hook config. Idempotent.

        Must make a `.bak` of the original config before writing. Must only
        touch entries tagged with the namespace key.
        """

    @abstractmethod
    def uninstall_hook(self, namespace: str = "agy-route") -> bool:
        """Remove hook entries tagged with our namespace. Returns True if any were removed."""