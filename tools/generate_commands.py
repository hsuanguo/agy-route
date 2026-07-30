#!/usr/bin/env python3
"""Verification tool for slash-command specifications in `src/agy_route/specs/`.

Validates that all command specs load correctly and can render target markdowns for
both Claude Code and opencode.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add src to sys.path for direct repository invocation
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from agy_route.specs import COMMAND_SPECS  # noqa: E402


def main() -> None:
    check_mode = "--check" in sys.argv

    print(f"Loaded {len(COMMAND_SPECS)} command spec(s):")
    for spec in COMMAND_SPECS:
        claude_rendered = spec.render_claude()
        opencode_rendered = spec.render_opencode()
        print(f" - {spec.name} (claude: {len(claude_rendered)} bytes, opencode: {len(opencode_rendered)} bytes)")

    if check_mode:
        print("All command specs verified successfully.")


if __name__ == "__main__":
    main()
