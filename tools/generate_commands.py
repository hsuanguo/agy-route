#!/usr/bin/env python3
"""Generate static Claude Code command files from command_specs.py."""
from pathlib import Path
from agy_route.specs.command_specs import COMMAND_SPECS

REPO_ROOT = Path(__file__).resolve().parent.parent
CLAUDE_CMDS_DIR = REPO_ROOT / "plugins" / "claude" / "commands"


def generate() -> None:
    CLAUDE_CMDS_DIR.mkdir(parents=True, exist_ok=True)
    for spec in COMMAND_SPECS:
        path = CLAUDE_CMDS_DIR / f"{spec.name}.md"
        path.write_text(spec.render_claude())
        print(f"Wrote {path.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    generate()
