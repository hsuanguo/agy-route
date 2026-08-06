import sys
from unittest.mock import patch
import pytest

from agy_route.core.executor import (
    EXIT_AUTH,
    EXIT_EMPTY,
    EXIT_OK,
    EXIT_QUOTA,
    build_full_prompt,
    classify_empty,
    emit_json_envelope,
    invoke_agy,
)


def test_build_full_prompt_without_prefix():
    prompt = build_full_prompt("POLICY TEXT", "user query")
    assert "POLICY TEXT" in prompt
    assert "user query" in prompt
    assert "User question:" in prompt


def test_build_full_prompt_with_prefix():
    prompt = build_full_prompt("POLICY TEXT", "user query", prefix="Sub-question: ")
    assert "POLICY TEXT" in prompt
    assert "Sub-question: user query" in prompt


def test_classify_empty():
    assert classify_empty("Error: 429 Resource Exhausted") == (EXIT_QUOTA, "quota")
    assert classify_empty("Unauthenticated user credentials") == (EXIT_AUTH, "auth")
    assert classify_empty("Unknown random error") == (EXIT_EMPTY, "empty_output")


def test_emit_json_envelope(capsys):
    emit_json_envelope(
        success=True,
        type_name="search",
        model="gemini-2.5-flash",
        duration_s=2,
        response="Search result",
    )
    captured = capsys.readouterr()
    assert '"success": true' in captured.out
    assert '"type": "search"' in captured.out
    assert '"model_used": "gemini-2.5-flash"' in captured.out
    assert '"response": "Search result"' in captured.out


def test_invoke_agy_passes_model():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "ok"
        mock_run.return_value.stderr = ""

        code, out, err = invoke_agy(
            "full prompt",
            "search",
            timeout_s=30,
            pass_model="gemini-2.5-flash",
        )
        assert code == EXIT_OK
        assert out == "ok"
        args, kwargs = mock_run.call_args
        cmd = args[0]
        assert "--model" in cmd
        assert "gemini-2.5-flash" in cmd
