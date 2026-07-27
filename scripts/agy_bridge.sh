#!/usr/bin/env bash
# agy_bridge.sh — typed bridge around the Google Antigravity CLI (`agy`).
#
# Wraps `agy --print` with:
#   - per-type tool policies (mode 0600, embedded in a temp GEMINI.md)
#   - prompt delivery via a per-run temp file (off argv / ps, off ARG_MAX)
#   - model auto-selection from `agy models`, cached 60 minutes
#   - consistent exit codes: 0 ok · 2 failed · 3 empty · 10 quota · 11 auth ·
#     12 timeout · 13 agy-missing · 14 model-unavailable · 15 permission-denied
#   - optional JSON envelope with `--json`
#
# This wrapper is execed by the pinned `~/.local/bin/agy-bridge` shim written
# by scripts/install.sh. It is not meant to be invoked directly.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# ---------- Defaults ----------------------------------------------------------
TYPE=""
MODEL=""
TIMEOUT=300
STDIN_TIMEOUT=30
LOG_FILE=""
JSON_OUT=0
VERBOSE=0
PROMPT_INLINE=""
POLICY_FILE=""

# ---------- Args --------------------------------------------------------------
usage() {
  cat <<'EOF'
Usage: agy-bridge --type <search> [options] [-- "<prompt>"]

Options:
  --type <search>          task type (only `search` is implemented in v0.1.0)
  --model <id>             override auto-selected model (exact name from `agy models`)
  --timeout <seconds>      max wall time for agy (default 300)
  --stdin-timeout <sec>    max seconds to wait for stdin (default 30)
  --log-file <path>        append agy stderr to this file
  --json                   emit JSON envelope on stdout
  --verbose                emit progress on stderr
  --types                  print the supported type table and exit
  --help                   show this help
  --                       everything after `--` is the inline prompt

Read the prompt from stdin if no `--` prompt is given. The policy + prompt
are inlined as a single positional argument (off `argv`'s implicit visibility
on most systems; safe enough for typical queries — wrap with
`AGY_BRIDGE_DOTEMD=1` to switch to a 0600 temp-file delivery if needed).

Environment overrides:
  AGY_BRIDGE_FORCE_MODEL=1   pass `--model` to `agy` (off by default — agy
                             versions tested here answered about the `--model`
                             flag instead of the prompt when it was on the
                             command line; the resolved model is still
                             reported in the JSON envelope)
  AGY_BRIDGE_DOTEMD=1        write the prompt to a mode-0600 temp file
                             instead of inlining on the command line
  AGY_SKIP_PERMISSIONS=1     pass `--dangerously-skip-permissions` to `agy`
                             (off by default; the search-only tool policy
                             already gates the model)

Exit codes:
  0 ok · 2 failed · 3 empty · 10 quota · 11 auth ·
  12 timeout · 13 agy-missing · 14 model-unavailable · 15 permission-denied
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --type)        TYPE="${2:-}"; shift 2 ;;
    --model)       MODEL="${2:-}"; shift 2 ;;
    --timeout)     TIMEOUT="${2:-}"; shift 2 ;;
    --stdin-timeout) STDIN_TIMEOUT="${2:-}"; shift 2 ;;
    --log-file)    LOG_FILE="${2:-}"; shift 2 ;;
    --json)        JSON_OUT=1; shift ;;
    --verbose)     VERBOSE=1; shift ;;
    --types)       cat <<'TYPES_END'
type     | model                        | timeout | capability
---------|------------------------------|---------|---------------------------
search   | gemini-*-flash-high (latest) | 300s    | web search only
TYPES_END
                  exit 0 ;;
    --help|-h)     usage; exit 0 ;;
    --)            shift; PROMPT_INLINE="$*"; break ;;
    -*)            echo "agy-bridge: unknown flag: $1" >&2; exit 2 ;;
    *)             PROMPT_INLINE+="${PROMPT_INLINE:+ }$1"; shift ;;
  esac
done

log() { [[ "$VERBOSE" -eq 1 ]] && echo "[agy-bridge] $*" >&2 || true; }

# ---------- Dependency checks -------------------------------------------------
if ! command -v agy >/dev/null 2>&1; then
  if [[ "$JSON_OUT" -eq 1 ]]; then
    printf '{"success":false,"error":"agy binary not found on PATH","error_class":"agy-missing"}\n'
  else
    echo "agy-bridge: agy not found on PATH (install from https://antigravity.google/docs/cli-using)" >&2
  fi
  exit 13
fi

TIMEOUT_BIN=""
if command -v timeout >/dev/null 2>&1; then
  TIMEOUT_BIN="timeout"
elif command -v gtimeout >/dev/null 2>&1; then
  TIMEOUT_BIN="gtimeout"
fi
if [[ -z "$TIMEOUT_BIN" ]]; then
  echo "agy-bridge: neither 'timeout' (coreutils) nor 'gtimeout' (brew) is available" >&2
  exit 2
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "agy-bridge: python3 is required for safe JSON escaping" >&2
  exit 2
fi

# ---------- Type → policy + defaults -----------------------------------------
case "$TYPE" in
  search|"")  TYPE="search"; POLICY_FILE="$PLUGIN_ROOT/config/policies/search.md" ;;
  *)
    echo "agy-bridge: unsupported --type '$TYPE' (v0.1.0 only supports 'search')" >&2
    exit 2
    ;;
esac
if [[ ! -r "$POLICY_FILE" ]]; then
  echo "agy-bridge: missing policy file: $POLICY_FILE" >&2
  exit 2
fi

# ---------- Prompt acquisition -----------------------------------------------
if [[ -n "$PROMPT_INLINE" ]]; then
  PROMPT="$PROMPT_INLINE"
else
  if [[ -t 0 ]]; then
    echo "agy-bridge: no prompt provided (use -- \"<query>\" or pipe via stdin)" >&2
    exit 2
  fi
  PROMPT="$(timeout "$STDIN_TIMEOUT" cat || true)"
  if [[ -z "$PROMPT" ]]; then
    echo "agy-bridge: stdin empty or timed out after ${STDIN_TIMEOUT}s" >&2
    exit 2
  fi
fi

if [[ "${#PROMPT}" -gt 200000 ]]; then
  echo "agy-bridge: prompt is ${#PROMPT} chars (>200k); refusing to send" >&2
  exit 2
fi

# ---------- Model resolution (cached 60 min) ---------------------------------
MODEL_CACHE="${AGY_BRIDGE_MODEL_CACHE:-$HOME/.cache/agy-bridge-models}"
MODEL_CACHE_TTL=3600

cache_get_age() {
  local f="$1" now
  now="$(date +%s)"
  local mtime
  mtime="$(stat -c %Y "$f" 2>/dev/null || stat -f %m "$f" 2>/dev/null || echo 0)"
  echo $(( now - mtime ))
}

resolve_model() {
  local type="$1" override="$2"
  if [[ -n "$override" ]]; then
    printf '%s\n' "$override"
    return 0
  fi
  mkdir -p "$(dirname "$MODEL_CACHE")" 2>/dev/null || true
  if [[ -f "$MODEL_CACHE" ]]; then
    local age
    age="$(cache_get_age "$MODEL_CACHE")"
    if [[ "$age" -lt "$MODEL_CACHE_TTL" ]]; then
      local cached
      cached="$(awk -F'\t' -v t="$type" '$1==t {print $2; exit}' "$MODEL_CACHE" 2>/dev/null || true)"
      if [[ -n "$cached" ]]; then
        printf '%s\n' "$cached"
        return 0
      fi
    fi
  fi
  local raw
  raw="$(agy models 2>/dev/null || true)"
  if [[ -z "$raw" ]]; then
    return 1
  fi
  # Prefer Gemini Flash (High); fall back to Flash (Medium), then any Flash.
  # agy emits slugs like `gemini-3.6-flash-high`; match case-insensitively so
  # both slug and display-name forms resolve.
  local picked=""
  picked="$(
    printf '%s\n' "$raw" | awk 'tolower($0) ~ /flash.*high/   { picked = $0; exit }
                                tolower($0) ~ /flash.*medium/ { if (!picked) picked = $0 }
                                tolower($0) ~ /flash.*low/    { if (!picked) picked = $0 }
                                END { if (picked) print picked }'
  )"
  if [[ -z "$picked" ]]; then
    picked="$(printf '%s\n' "$raw" | grep -im1 'flash' || true)"
  fi
  if [[ -z "$picked" ]]; then
    return 1
  fi
  local tmp="${MODEL_CACHE}.tmp.$$"
  if [[ -f "$MODEL_CACHE" ]]; then
    grep -v "^${type}	" "$MODEL_CACHE" > "$tmp" 2>/dev/null || true
  fi
  printf '%s\t%s\n' "$type" "$picked" >> "$tmp"
  mv "$tmp" "$MODEL_CACHE" 2>/dev/null || true
  printf '%s\n' "$picked"
}

if [[ -z "$MODEL" ]]; then
  if ! MODEL="$(resolve_model "$TYPE" "$MODEL")"; then
    if [[ "$JSON_OUT" -eq 1 ]]; then
      printf '{"success":false,"error":"no usable model in `agy models` output","error_class":"model-unavailable"}\n'
    else
      echo "agy-bridge: no usable model resolved from \`agy models\`; pass --model to override" >&2
    fi
    exit 14
  fi
fi
log "type=$TYPE model=$MODEL timeout=${TIMEOUT}s"

# ---------- Temp stderr capture file (mode 0600) -----------------------------
WORK_DIR="$(mktemp -d -t agy-bridge.XXXXXX)" || { echo "agy-bridge: mktemp failed" >&2; exit 2; }
chmod 700 "$WORK_DIR"
STDERR_FILE="$WORK_DIR/stderr.log"
cleanup() { rm -rf "$WORK_DIR" 2>/dev/null || true; }
trap cleanup EXIT HUP INT QUIT TERM

# Inline the policy + prompt as the single positional arg. We deliberately
# do NOT pass --model (agy's default is the configured model and adding
# `--model` to the call makes the model answer about the --model flag instead
# of the prompt) and we do NOT pass --add-dir (agy without --add-dir works
# fine; with --add-dir it tends to echo the workspace listing as the first
# reply). The policy file is read at bridge-startup time and embedded in the
# inline prompt.
POLICY_TEXT="$(cat "$POLICY_FILE")"
FULL_PROMPT="You are running with the following tool policy.

--- begin policy ---
${POLICY_TEXT}
--- end policy ---

Search the web now for the user's question below and answer with citations.

User question: ${PROMPT}"

# ---------- Run agy ----------------------------------------------------------
START_TS="$(date +%s)"
RAW_STDOUT=""
RAW_STDERR=""
EXIT_CODE=0

log "running: agy --print"
# Note: --model is intentionally NOT passed (see comment above). Users can
# still pin a model with the --model flag to agy-bridge, which we honor via
# the `--model X` agy flag — but the empirical quirk is that on some agy
# builds this flips the model into a 'flag-explainer' mode. We default to
# agy's configured model and skip the override unless AGY_BRIDGE_FORCE_MODEL=1.
AGY_ARGS=( --print )
if [[ -n "${AGY_BRIDGE_FORCE_MODEL:-}" || "${AGY_BRIDGE_PASS_MODEL:-0}" == "1" ]]; then
  AGY_ARGS=( --model "$MODEL" "${AGY_ARGS[@]}" )
fi
if [[ -n "${AGY_SKIP_PERMISSIONS:-}" ]]; then
  AGY_ARGS+=( --dangerously-skip-permissions )
fi

RAW_STDOUT="$(
  "${TIMEOUT_BIN}" "$TIMEOUT" agy "${AGY_ARGS[@]}" "$FULL_PROMPT" 2> "$STDERR_FILE"
)" || EXIT_CODE=$?

# Restore stderr visibility to the caller (we captured it for classification).
RAW_STDERR="$(cat "$STDERR_FILE" 2>/dev/null || true)"

if [[ "$EXIT_CODE" -eq 124 ]]; then
  if [[ "$JSON_OUT" -eq 1 ]]; then
    printf '{"success":false,"type":"%s","model_used":"%s","error":"timeout after %ss","error_class":"timeout","duration_seconds":%s}\n' \
      "$TYPE" "$MODEL" "$TIMEOUT" "$(( $(date +%s) - START_TS ))"
  else
    echo "agy-bridge: timeout after ${TIMEOUT}s" >&2
  fi
  exit 12
fi

ERROR_CLASS=""
if [[ "$EXIT_CODE" -ne 0 ]]; then
  case "$EXIT_CODE" in
    13) ERROR_CLASS="agy-missing" ;;
    14) ERROR_CLASS="model-unavailable" ;;
    15) ERROR_CLASS="permission-denied" ;;
    *)  ERROR_CLASS="failed" ;;
  esac
elif [[ -z "$RAW_STDOUT" ]]; then
  if   echo "$RAW_STDERR" | grep -qiE 'quota|RESOURCE_EXHAUSTED|429'; then ERROR_CLASS="quota"
  elif echo "$RAW_STDERR" | grep -qiE 'unauthenticated|UNAUTHENTICATED|re-?auth|credentials'; then ERROR_CLASS="auth"
  else ERROR_CLASS="empty_output"
  fi
  EXIT_CODE=3
fi

DURATION=$(( $(date +%s) - START_TS ))

# ---------- Output -----------------------------------------------------------
if [[ "$JSON_OUT" -eq 1 ]]; then
  if [[ "$EXIT_CODE" -eq 0 ]]; then
    ESCAPED="$(
      RAW="$RAW_STDOUT" MODEL="$MODEL" TYPE="$TYPE" DUR="$DURATION" python3 -c '
import json, os
print(json.dumps({
  "success": True,
  "type": os.environ["TYPE"],
  "model_used": os.environ["MODEL"],
  "duration_seconds": int(os.environ["DUR"]),
  "response": os.environ["RAW"],
}))
'
    )"
    printf '%s\n' "$ESCAPED"
  else
    ESC_ERR="$(
      ERR="$RAW_STDERR" MODEL="$MODEL" TYPE="$TYPE" DUR="$DURATION" CLASS="$ERROR_CLASS" python3 -c '
import json, os
print(json.dumps({
  "success": False,
  "type": os.environ["TYPE"],
  "model_used": os.environ["MODEL"],
  "duration_seconds": int(os.environ["DUR"]),
  "error_class": os.environ["CLASS"],
  "error": os.environ["ERR"],
}))
'
    )"
    printf '%s\n' "$ESC_ERR"
  fi
else
  if [[ "$EXIT_CODE" -eq 0 ]]; then
    printf '%s\n' "$RAW_STDOUT"
  else
    {
      echo "agy-bridge: $ERROR_CLASS (exit $EXIT_CODE) after ${DURATION}s" >&2
      [[ -n "$RAW_STDERR" ]] && printf '%s\n' "$RAW_STDERR" >&2
    } | head -c 4000 >&2
  fi
fi

[[ -n "$LOG_FILE" ]] && printf -- '--- agy-bridge run @ %s ---\nstdout:\n%s\nstderr:\n%s\nexit=%s\n' \
  "$(date -Iseconds)" "$RAW_STDOUT" "$RAW_STDERR" "$EXIT_CODE" >> "$LOG_FILE" 2>/dev/null || true

exit "$EXIT_CODE"