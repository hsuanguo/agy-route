"""agy-route hook handlers for Claude Code.

These are wired up by the plugin's `hooks/hooks.json`. Each handler reads a
JSON payload from stdin (the Claude Code hook protocol) and emits a JSON
decision on stdout.
"""