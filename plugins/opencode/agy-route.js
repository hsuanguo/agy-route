/**
 * agy-route — opencode plugin
 *
 * Intercepts opencode's `websearch` tool calls and reroutes them to
 * `agy-route search`. Opencode auto-loads `.js` files dropped into
 * `~/.config/opencode/plugins/` (no `cfg.plugin` registration needed).
 *
 * Recovery message mirrors the Python `agy-route-hook-pretooluse` so
 * Claude's behavior is identical between Claude Code and opencode.
 */

export const AgyRoutePlugin = async () => {
  return {
    "tool.execute.before": async (input, output) => {
      if (input.tool !== "websearch") return
      // Same denial message as agy-route-hook-pretooluse.
      // Force opencode's model to call agy-route search via Bash instead.
      throw new Error(
        "WebSearch is replaced by `agy-route search` " +
        "(a policy-gated, grounded alternative that uses the agy CLI's " +
        "`search_web` tool with source citations). Run via Bash instead:\n\n" +
        "  agy-route search \"<your query>\"\n\n" +
        "If `agy-route` is not on $PATH, install it once with " +
        "`uv tool install git+https://github.com/hsuanguo/agy-route`, then retry."
      )
    },
  }
}
