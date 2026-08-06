"""Target ABC — one implementation per agent (Claude Code, opencode, …)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

HookFormat = Literal["json", "jsonc", "toml"]


@dataclass
class TargetInstallResult:
    target: str
    skill_installed: bool
    skill_path: str | None
    hook_installed: bool
    plugin_installed: bool
    commands_installed: list[str] = field(default_factory=list)
    skill_paths: list[str] = field(default_factory=list)
    hook_path: str | None = None
    plugin_path: str | None = None
    skill_changed: bool = False
    hook_changed: bool = False
    plugin_changed: bool = False
    message: str = ""


@dataclass
class TargetUninstallResult:
    target: str
    skills_removed: list[str] = field(default_factory=list)
    hook_removed: bool = False
    plugin_removed: bool = False
    commands_removed: list[str] = field(default_factory=list)


class Target(ABC):
    """A target agent's settings layout (skill dir + hook config path/format).

    Concrete targets implement polymorphic installation (`install_target`)
    and uninstallation (`uninstall_target`).
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
        """Whether this target is detectable on the host."""

    @abstractmethod
    def install_target(
        self,
        *,
        with_hook: bool = False,
        skill_only: bool = False,
        hook_only: bool = False,
        dry_run: bool = False,
        skills: tuple[str, ...] = ("agy-web-search", "agy-research"),
        namespace: str = "agy-route",
    ) -> TargetInstallResult:
        """Install skills, hooks, plugins, or commands for this target."""

    @abstractmethod
    def uninstall_target(
        self,
        *,
        skills: tuple[str, ...] = ("agy-web-search", "agy-research"),
        namespace: str = "agy-route",
    ) -> TargetUninstallResult:
        """Uninstall skills, hooks, plugins, and commands for this target."""