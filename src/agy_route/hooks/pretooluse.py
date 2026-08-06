"""PreToolUse hook handler — runs on Claude Code's WebSearch tool.

Goal: every WebSearch tool call gets routed to `agy-route search` (which
uses the agy CLI's grounded search instead of Claude's built-in WebSearch).

Claude Code's hook protocol fires this script with a JSON payload on stdin:

    {
      "tool_name": "WebSearch",
      "tool_input": {"query": "...", "allowed_domains": [...], ...}
    }

We respond on stdout with a JSON object:

    {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                            "permissionDecision": "deny",
                            "permissionDecisionReason": "..."}}

When the WebSearch call is denied, Claude sees the denial reason as a tool
error and recovers by calling the Bash tool with the suggested
`agy-route search "<query>"` command instead. The model has all it needs
in the denial reason: the exact command, the binary name, and a reminder
of what `agy-route` is.

The hook stays fast (<50 ms cold path): no network, no agy invocation here.
That happens in the Bash call the model makes next.
"""
from __future__ import annotations

import json
import sys
from typing import Any


def _build_denial_reason(query: str, has_filters: bool) -> str:
    """Construct the reason text shown to Claude as the tool-error message.

    The message is intentionally short and branded — Claude Code wraps
    `permissionDecision: "deny"` outputs in an "Error:" prefix that looks
    alarming, but the body itself is a friendly redirect hint, not a
    failure. Keeping the prose minimal makes the redirect scannable.
    """
    q = query.strip()
    if has_filters:
        # WebSearch had allowed_domains / blocked_domains. agy-route doesn't
        # forward those today; tell the model to drop the filter for this call.
        return (
            "[agy-route] redirecting WebSearch → agy-route search "
            "(drop allowed/blocked-domains for this call):\n\n"
            f"  agy-route search \"{q}\""
        )
    return (
        "[agy-route] redirecting WebSearch → agy-route search:\n\n"
        f"  agy-route search \"{q}\""
    )


def _coerce_query(tool_input: dict[str, Any]) -> tuple[str, bool]:
    """Pull the query out of WebSearch's tool_input. Returns (query, has_filters)."""
    if not isinstance(tool_input, dict):
        return "", False
    q = tool_input.get("query")
    if not isinstance(q, str):
        q = ""
    has_filters = bool(
        tool_input.get("allowed_domains") or tool_input.get("blocked_domains")
    )
    return q, has_filters


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError) as err:
        # Malformed payload — log to stderr and let the original tool call proceed
        # so we don't accidentally break Claude over a bug in our hook.
        sys.stderr.write(f"[agy-route pretooluse] warning: malformed stdin payload: {err}\n")
        json.dump({"continue": True, "suppressOutput": True}, sys.stdout)
        return 0

    tool_name = payload.get("tool_name") if isinstance(payload, dict) else None
    if tool_name != "WebSearch":
        # Not our concern — pass through.
        json.dump({"continue": True, "suppressOutput": True}, sys.stdout)
        return 0

    tool_input = payload.get("tool_input") if isinstance(payload, dict) else {}
    query, has_filters = _coerce_query(tool_input if isinstance(tool_input, dict) else {})

    reason = _build_denial_reason(query, has_filters)
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            },
            "suppressOutput": False,
        },
        sys.stdout,
    )
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":  # pragma: no cover
    main()