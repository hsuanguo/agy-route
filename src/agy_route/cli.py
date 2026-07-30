"""CLI for `agy-route`.

A Typer app that wraps `agy --print` with:
  - per-type tool policies (inlined as part of the prompt)
  - model auto-resolution from `agy models`, cached 60 minutes
  - stable exit codes: 0 · 2 · 3 · 10 (quota) · 11 (auth) · 12 (timeout) ·
    13 (agy-missing) · 14 (model-unavailable) · 15 (permission-denied)
  - optional `--json` envelope on stdout
"""
from __future__ import annotations

import os
import shutil
import sys
import time
from pathlib import Path
from typing import Optional

import typer

from agy_route.core.executor import (
    EXIT_AGY_MISSING,
    EXIT_FAILED,
    EXIT_MODEL_UNAVAILABLE,
    EXIT_OK,
    EXIT_TIMEOUT,
    build_full_prompt,
    classify_empty,
    emit_json_envelope,
    invoke_agy,
)
from agy_route.core.models import ResolvedModel, resolve_model
from agy_route.core.policy import find_policy

app = typer.Typer(
    name="agy-route",
    help="Typed, policy-gated proxy in front of the `agy` CLI.",
    no_args_is_help=True,
    add_completion=False,
)


@app.command("types")
def types_cmd() -> None:
    """Print the supported (type, model, timeout) table and exit."""
    typer.echo(
        "type     | model                        | timeout | capability\n"
        "---------|------------------------------|---------|---------------------------\n"
        "search   | gemini-*-flash-high (latest) | 300s    | web search only"
    )
    raise typer.Exit(EXIT_OK)


@app.command("targets")
def targets_cmd() -> None:
    """List supported install targets (Claude Code, opencode, …)."""
    from agy_route.targets import all_targets

    rows = []
    for t in all_targets():
        present = "yes" if t.is_present() else "no"
        rows.append(
            f"{t.name:<8} | {t.description}\n"
            f"         | config_dir = {t.config_dir}\n"
            f"         | hook_config = {t.hook_config_path} ({t.hook_config_format})\n"
            f"         | present on host: {present}"
        )
    typer.echo("\n\n".join(rows))
    raise typer.Exit(EXIT_OK)


@app.command("install")
def install_cmd(
    target: str = typer.Option(
        "claude",
        "--target",
        "-t",
        help="Which agent to install for (claude, opencode, …). Run `agy-route targets` to list.",
    ),
    skill_only: bool = typer.Option(
        False, "--skill-only", help="Install only the SKILL.md, not the hook."
    ),
    hook_only: bool = typer.Option(
        False, "--hook-only", help="Install only the PreToolUse hook, not the skill."
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Don't touch the filesystem; just report what would change.",
    ),
) -> None:
    """Install the SKILL.md and/or PreToolUse hook into the target agent."""
    from agy_route import install as install_mod

    if skill_only and hook_only:
        typer.echo("agy-route install: --skill-only and --hook-only are mutually exclusive", err=True)
        raise typer.Exit(EXIT_FAILED)

    try:
        result = install_mod.install(
            target, skill_only=skill_only, hook_only=hook_only, dry_run=dry_run
        )
    except KeyError as e:
        typer.echo(f"agy-route install: {e}", err=True)
        raise typer.Exit(EXIT_FAILED) from None

    if result.message:
        typer.echo(f"agy-route install: {result.message}", err=True)
        raise typer.Exit(EXIT_FAILED)

    if dry_run:
        typer.echo(
            f"[dry-run] target={result.target} "
            f"skill_installed={result.skill_installed} (changed={result.skill_changed}) "
            f"hook_installed={result.hook_installed}"
        )
    else:
        actions = []
        if not hook_only and result.skill_path:
            actions.append(f"skill → {result.skill_path}")
        if not skill_only and (result.hook_installed or result.plugin_installed):
            actions.append(f"hook/plugin → {target}")
        if actions:
            typer.echo("installed: " + "; ".join(actions))
        else:
            typer.echo(f"nothing to install for target {target!r}")
    raise typer.Exit(EXIT_OK)


@app.command("uninstall")
def uninstall_cmd(
    target: str = typer.Option(
        None,
        "--target",
        "-t",
        help="Which agent to uninstall from. Omit to scan all registered targets.",
    ),
) -> None:
    """Remove the SKILL.md and hook entries previously installed by `agy-route install`."""
    from agy_route import install as install_mod

    if target is None:
        results = install_mod.uninstall_all()
        any_removed = False
        for name, (skill_removed, hook_removed) in results.items():
            if skill_removed or hook_removed:
                any_removed = True
                typer.echo(
                    f"{name}: removed skill={skill_removed} hook={hook_removed}"
                )
            else:
                typer.echo(f"{name}: nothing to remove")
        if not any_removed:
            typer.echo("nothing to remove")
    else:
        try:
            skill_removed, hook_removed = install_mod.uninstall(target)
        except KeyError as e:
            typer.echo(f"agy-route uninstall: {e}", err=True)
            raise typer.Exit(EXIT_FAILED) from None
        typer.echo(
            f"{target}: removed skill={skill_removed} hook={hook_removed}"
        )
    raise typer.Exit(EXIT_OK)


@app.command("search")
def search_cmd(
    prompt: Optional[str] = typer.Argument(
        None,
        show_default=False,
        help="Search query. If omitted, the prompt is read from stdin (with a 30s timeout by default).",
    ),
    timeout: int = typer.Option(
        300,
        "--timeout",
        help="Max wall time (seconds) for the underlying agy call.",
    ),
    stdin_timeout: int = typer.Option(
        30,
        "--stdin-timeout",
        help="Max seconds to wait for a prompt from stdin.",
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model",
        help="Override the auto-selected model. Exact name from `agy models`.",
    ),
    log_file: Optional[Path] = typer.Option(
        None,
        "--log-file",
        help="Append agy's stderr + result metadata here.",
    ),
    as_json: bool = typer.Option(
        False,
        "--json",
        help="Emit a JSON envelope on stdout.",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        help="Print progress on stderr.",
    ),
) -> None:
    """Run a web search via agy (search-only tool policy)."""
    _run(
        type_name="search",
        prompt=prompt,
        timeout=timeout,
        stdin_timeout=stdin_timeout,
        model=model,
        log_file=log_file,
        as_json=as_json,
        verbose=verbose,
    )


# ---------- Deep-research sub-group -------------------------------------------

research_app = typer.Typer(
    name="research",
    help=(
        "Deep-research primitives (fetch + quote). Used by the "
        "/agy-research slash command and the agy-route-research skill."
    ),
    no_args_is_help=True,
    add_completion=False,
)
app.add_typer(research_app)


@research_app.command("fetch")
def research_fetch_cmd(
    sub_question: Optional[str] = typer.Argument(
        None,
        show_default=False,
        help="Sub-question to research. If omitted, the prompt is read from stdin.",
    ),
    timeout: int = typer.Option(300, "--timeout"),
    stdin_timeout: int = typer.Option(30, "--stdin-timeout"),
    model: Optional[str] = typer.Option(None, "--model"),
    log_file: Optional[Path] = typer.Option(None, "--log-file"),
    as_json: bool = typer.Option(False, "--json"),
    verbose: bool = typer.Option(False, "--verbose"),
) -> None:
    """Fan-out sub-question search via agy. Returns 5-8 bullet findings + URLs + dates."""
    prompt_prefix = (
        "Use web search for the following sub-question. Return 5-8 bullet "
        "findings, each with the exact source URL and publication date. "
        "Output ONLY the findings, URLs, and dates — no synthesis, no "
        "narrative, no commentary.\n\n"
        "Sub-question: "
    )
    _run(
        type_name="search",
        prompt=sub_question,
        timeout=timeout,
        stdin_timeout=stdin_timeout,
        model=model,
        log_file=log_file,
        as_json=as_json,
        verbose=verbose,
        prompt_prefix=prompt_prefix,
    )


@research_app.command("quote")
def research_quote_cmd(
    claim: str = typer.Argument(..., help="The claim to verify (quoted)."),
    url: str = typer.Argument(..., help="The URL to fetch + quote from."),
    timeout: int = typer.Option(300, "--timeout"),
    model: Optional[str] = typer.Option(None, "--model"),
    log_file: Optional[Path] = typer.Option(None, "--log-file"),
    as_json: bool = typer.Option(False, "--json"),
    verbose: bool = typer.Option(False, "--verbose"),
) -> None:
    """Open <url> and quote the verbatim sentence(s) supporting <claim>."""
    prompt = (
        f"Open {url} and quote the exact sentence(s) supporting: "
        f"'{claim}'. If the page does not support it, reply NOT SUPPORTED."
    )
    _run(
        type_name="search",
        prompt=prompt,
        timeout=timeout,
        stdin_timeout=30,
        model=model,
        log_file=log_file,
        as_json=as_json,
        verbose=verbose,
        prompt_prefix="",
    )


# ---------- Shared runner -----------------------------------------------------


def _run(
    *,
    type_name: str,
    prompt: Optional[str],
    timeout: int,
    stdin_timeout: int,
    model: Optional[str],
    log_file: Optional[Path],
    as_json: bool,
    verbose: bool,
    prompt_prefix: str = "",
) -> None:
    def log(msg: str) -> None:
        if verbose:
            typer.echo(f"[agy-route] {msg}", err=True)

    if not shutil.which("agy"):
        _fail(
            type_name=type_name,
            model="",
            as_json=as_json,
            exit_code=EXIT_AGY_MISSING,
            error_class="agy-missing",
            message="agy binary not found on PATH (install from https://antigravity.google/docs/cli-using)",
            stderr="",
            duration_s=0,
            log_file=log_file,
        )
        return

    # Acquire prompt.
    if prompt is None:
        if sys.stdin.isatty():
            _fail(
                type_name=type_name,
                model="",
                as_json=as_json,
                exit_code=EXIT_FAILED,
                error_class="failed",
                message="no prompt provided (pass it as the first arg or pipe via stdin)",
                stderr="",
                duration_s=0,
                log_file=log_file,
            )
            return
        try:
            prompt = _read_stdin(stdin_timeout)
        except TimeoutError:
            _fail(
                type_name=type_name,
                model="",
                as_json=as_json,
                exit_code=EXIT_FAILED,
                error_class="failed",
                message=f"stdin empty or timed out after {stdin_timeout}s",
                stderr="",
                duration_s=0,
                log_file=log_file,
            )
            return
    if not prompt.strip():
        _fail(
            type_name=type_name,
            model="",
            as_json=as_json,
            exit_code=EXIT_FAILED,
            error_class="failed",
            message="prompt is empty",
            stderr="",
            duration_s=0,
            log_file=log_file,
        )
        return
    if len(prompt) > 200_000:
        _fail(
            type_name=type_name,
            model="",
            as_json=as_json,
            exit_code=EXIT_FAILED,
            error_class="failed",
            message=f"prompt is {len(prompt)} chars (>200k); refusing to send",
            stderr="",
            duration_s=0,
            log_file=log_file,
        )
        return

    # Resolve the model.
    if model:
        resolved = ResolvedModel(name=model, from_cache=False)
    else:
        resolved = resolve_model(type_name, override=None)
        if not resolved.name:
            _fail(
                type_name=type_name,
                model="",
                as_json=as_json,
                exit_code=EXIT_MODEL_UNAVAILABLE,
                error_class="model-unavailable",
                message="no usable model resolved from `agy models`; pass --model to override",
                stderr="",
                duration_s=0,
                log_file=log_file,
            )
            return
    log(f"type={type_name} model={resolved.name} timeout={timeout}s")

    # Find + inline the policy.
    try:
        policy_text = find_policy(type_name)
    except FileNotFoundError as e:
        _fail(
            type_name=type_name,
            model=resolved.name,
            as_json=as_json,
            exit_code=EXIT_FAILED,
            error_class="failed",
            message=str(e),
            stderr="",
            duration_s=0,
            log_file=log_file,
        )
        return
    full_prompt = build_full_prompt(policy_text, prompt, prefix=prompt_prefix)

    # Invoke agy.
    pass_model = (
        resolved.name if (resolved.name and os.environ.get("AGY_ROUTE_FORCE_MODEL"))
        else None
    )
    start = time.monotonic()
    code, stdout, stderr = invoke_agy(
        full_prompt,
        type_name,
        timeout_s=timeout,
        pass_model=pass_model,
    )
    duration_s = int(time.monotonic() - start)

    # Classify failures.
    error_class: Optional[str] = None
    if code != 0:
        error_class = {
            13: "agy-missing",
            14: "model-unavailable",
            15: "permission-denied",
        }.get(code, "failed")
        if code == EXIT_TIMEOUT:
            pass
    elif not stdout:
        rc, ec = classify_empty(stderr)
        code = rc
        error_class = ec

    if code != 0:
        _fail(
            type_name=type_name,
            model=resolved.name,
            as_json=as_json,
            exit_code=code,
            error_class=error_class or "failed",
            message=(stderr or error_class or "unknown error")[:4000],
            stderr=stderr,
            duration_s=duration_s,
            log_file=log_file,
        )
        return

    if as_json:
        emit_json_envelope(
            success=True,
            type_name=type_name,
            model=resolved.name,
            duration_s=duration_s,
            response=stdout,
        )
    else:
        sys.stdout.write(stdout)
        if not stdout.endswith("\n"):
            sys.stdout.write("\n")

    _maybe_log(log_file, type_name, resolved.name, stdout, stderr, code, duration_s)


def _read_stdin(timeout_s: int) -> str:
    import select

    readable, _, _ = select.select([sys.stdin], [], [], timeout_s)
    if not readable:
        raise TimeoutError("stdin read timed out")
    return sys.stdin.read()


def _fail(
    *,
    type_name: str,
    model: str,
    as_json: bool,
    exit_code: int,
    error_class: str,
    message: str,
    stderr: str,
    duration_s: int,
    log_file: Optional[Path],
) -> None:
    if as_json:
        emit_json_envelope(
            success=False,
            type_name=type_name,
            model=model,
            duration_s=duration_s,
            response=message,
            error_class=error_class,
        )
    else:
        typer.echo(f"agy-route: {error_class} (exit {exit_code}): {message}", err=True)
    _maybe_log(log_file, type_name, model, "", stderr, exit_code, duration_s)
    raise typer.Exit(exit_code)


def _maybe_log(
    log_file: Optional[Path],
    type_name: str,
    model: str,
    stdout: str,
    stderr: str,
    exit_code: int,
    duration_s: int,
) -> None:
    if not log_file:
        return
    try:
        with log_file.open("a") as fh:
            fh.write(
                f"--- agy-route run @ {time.strftime('%Y-%m-%dT%H:%M:%S%z')} "
                f"(type={type_name} model={model} exit={exit_code} duration={duration_s}s) ---\n"
                f"stdout:\n{stdout}\nstderr:\n{stderr}\n"
            )
    except OSError:
        pass


def main() -> None:
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
