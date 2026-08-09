"""Process execution and exit code handling for agy-route."""
from __future__ import annotations

import json
import os
import random
import re
import subprocess
import sys
import time
from typing import Optional

# Exit codes — kept stable for callers scripting around the wrapper.
EXIT_OK = 0
EXIT_FAILED = 2
EXIT_EMPTY = 3
EXIT_QUOTA = 10
EXIT_AUTH = 11
EXIT_TIMEOUT = 12
EXIT_AGY_MISSING = 13
EXIT_MODEL_UNAVAILABLE = 14
EXIT_PERMISSION_DENIED = 15


def build_full_prompt(policy_text: str, user_prompt: str, prefix: str = "") -> str:
    """Combine policy text and user prompt into a full prompt for agy."""
    if prefix:
        return (
            "You are running with the following tool policy.\n\n"
            "--- begin policy ---\n"
            f"{policy_text}\n"
            "--- end policy ---\n\n"
            f"{prefix}{user_prompt}"
        )
    return (
        "You are running with the following tool policy.\n\n"
        "--- begin policy ---\n"
        f"{policy_text}\n"
        "--- end policy ---\n\n"
        "Search the web now for the user's question below and answer with citations.\n\n"
        f"User question: {user_prompt}"
    )


def classify_empty(stderr: str) -> tuple[int, str]:
    """Classify why output was empty based on stderr content."""
    s = stderr.lower()
    if re.search(r"quota|resource_exhausted|429", s):
        return EXIT_QUOTA, "quota"
    if re.search(r"unauthenticated|re-?auth|credentials", s):
        return EXIT_AUTH, "auth"
    return EXIT_EMPTY, "empty_output"


RETRYABLE_PATTERN = re.compile(
    r"lock|busy|429|resource_exhausted|quota|connection|timeout|econnreset",
    re.IGNORECASE,
)
NON_RETRYABLE_PATTERN = re.compile(
    r"unauthenticated|re-?auth|credentials|permission_denied|not found",
    re.IGNORECASE,
)


def is_retryable_error(stdout: str, stderr: str) -> bool:
    """Return True if the failure is caused by transient lock contention, quota, or network issues."""
    combined = f"{stdout}\n{stderr}"
    if NON_RETRYABLE_PATTERN.search(combined):
        return False
    if not stdout.strip() or RETRYABLE_PATTERN.search(combined):
        return True
    return False


def invoke_agy(
    full_prompt: str,
    type_name: str,
    *,
    timeout_s: int,
    pass_model: Optional[str],
    max_retries: int = 2,
) -> tuple[int, str, str]:
    """Run `agy --print` with the inlined prompt, with automatic retry on lock/quota transient errors.

    Returns (exit_code, stdout, stderr).
    """
    agy_args: list[str] = ["agy", "--print"]
    if pass_model:
        agy_args += ["--model", pass_model]
    if os.environ.get("AGY_SKIP_PERMISSIONS"):
        agy_args.append("--dangerously-skip-permissions")
    agy_args.append(full_prompt)

    last_code = EXIT_EMPTY
    last_stdout = ""
    last_stderr = ""

    for attempt in range(max_retries + 1):
        if attempt > 0:
            time.sleep(random.uniform(0.3, 0.8) * attempt)

        try:
            completed = subprocess.run(
                agy_args,
                capture_output=True,
                text=True,
                timeout=timeout_s,
            )
        except FileNotFoundError:
            return EXIT_AGY_MISSING, "", "agy binary not found on PATH"
        except subprocess.TimeoutExpired:
            return EXIT_TIMEOUT, "", f"timeout after {timeout_s}s"

        last_code = completed.returncode
        last_stdout = completed.stdout
        last_stderr = completed.stderr

        if last_code == 0 and last_stdout.strip():
            return last_code, last_stdout, last_stderr

        if not is_retryable_error(last_stdout, last_stderr):
            break

    return last_code, last_stdout, last_stderr


def emit_json_envelope(
    *,
    success: bool,
    type_name: str,
    model: str,
    duration_s: int,
    response: str,
    error_class: Optional[str] = None,
) -> None:
    """Emit JSON envelope payload to stdout."""
    payload: dict[str, object] = {
        "success": success,
        "type": type_name,
        "model_used": model,
        "duration_seconds": duration_s,
    }
    if success:
        payload["response"] = response
    else:
        payload["error_class"] = error_class or "failed"
        payload["error"] = response
    json.dump(payload, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
