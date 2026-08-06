"""Source of truth and rendering engine for agy-route slash commands.

Each `CommandSpec` defines a slash command and can render markdown output
dynamically on the fly for Claude Code (`render_claude()`) and opencode
(`render_opencode()`).
"""
from __future__ import annotations

from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Optional

_LOCAL_BODIES_DIR = Path(__file__).resolve().parent / "bodies"


def _load_body(name: str) -> str:
    # 1. Try local filesystem (for dev / source checkout)
    local_path = _LOCAL_BODIES_DIR / f"{name}.md"
    if local_path.is_file():
        return local_path.read_text()
    # 2. Try package resources (for installed wheel)
    try:
        return (
            resources.files("agy_route.specs.bodies")
            .joinpath(f"{name}.md")
            .read_text()
        )
    except (FileNotFoundError, OSError):
        return ""


RESEARCH_FETCH_PROMPT_PREFIX = (
    "Use web search for the following sub-question. Return 5-8 bullet "
    "findings, each with the exact source URL and publication date. "
    "Output ONLY the findings, URLs, and dates — no synthesis, no "
    "narrative, no commentary.\n\n"
    "Sub-question: "
)

RESEARCH_QUOTE_PROMPT_TEMPLATE = (
    "Open {url} and quote the exact sentence(s) supporting: "
    "'{claim}'. If the page does not support it, reply NOT SUPPORTED."
)


@dataclass
class CommandSpec:
    name: str
    description: str
    argument_hint: Optional[str] = None
    body: str = ""
    # opencode-only optional fields
    opencode_agent: Optional[str] = None
    opencode_model: Optional[str] = None
    opencode_subtask: Optional[bool] = None

    def __post_init__(self) -> None:
        if not self.body and self.name:
            self.body = _load_body(self.name)

    @classmethod
    def load(cls, *, name: str, description: str, **kwargs) -> "CommandSpec":
        body = _load_body(name)
        return cls(name=name, description=description, body=body, **kwargs)

    def render_claude(self) -> str:
        """Render markdown formatted for Claude Code slash command."""
        lines = ["---", f"description: {self.description}"]
        if self.argument_hint:
            lines.append(f'argument-hint: "{self.argument_hint}"')
        lines.append("---")
        lines.append("")
        lines.append(self.body.rstrip())
        lines.append("")
        return "\n".join(lines)

    def render_opencode(self) -> str:
        """Render markdown formatted strictly for opencode slash command."""
        lines = ["---", f"description: {self.description}"]
        if self.opencode_agent:
            lines.append(f"agent: {self.opencode_agent}")
        if self.opencode_model:
            lines.append(f"model: {self.opencode_model}")
        if self.opencode_subtask is not None:
            lines.append(f"subtask: {'true' if self.opencode_subtask else 'false'}")
        lines.append("---")
        lines.append("")
        lines.append(self.body.rstrip())
        lines.append("")
        return "\n".join(lines)


COMMAND_SPECS: list[CommandSpec] = [
    CommandSpec.load(
        name="agy-web-search",
        description=(
            "Run a grounded web search via the agy CLI (Gemini, with citations). "
            "Drop-in for Claude's built-in WebSearch tool."
        ),
        argument_hint="<query>",
    ),
    CommandSpec.load(
        name="agy-research",
        description=(
            "Multi-source deep research via agy-route: plan, fan-out fetch, "
            "URL-quote verification, and cited synthesis."
        ),
        argument_hint="<topic>",
        opencode_subtask=True,
    ),
]
