import json
from io import StringIO
from unittest.mock import patch

from agy_route.hooks import pretooluse


def test_pretooluse_websearch_denied(capsys):
    input_payload = {
        "tool_name": "WebSearch",
        "tool_input": {"query": "python tutorial"},
    }
    with patch("sys.stdin", StringIO(json.dumps(input_payload))):
        code = pretooluse.main()
        assert code == 0

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "agy-route search \"python tutorial\"" in data["hookSpecificOutput"]["permissionDecisionReason"]


def test_pretooluse_other_tool_passed(capsys):
    input_payload = {
        "tool_name": "Bash",
        "tool_input": {"command": "ls"},
    }
    with patch("sys.stdin", StringIO(json.dumps(input_payload))):
        code = pretooluse.main()
        assert code == 0

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data == {"continue": True, "suppressOutput": True}


def test_pretooluse_malformed_input_logs_stderr(capsys):
    with patch("sys.stdin", StringIO("NOT JSON")):
        code = pretooluse.main()
        assert code == 0

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data == {"continue": True, "suppressOutput": True}
    assert "warning: malformed stdin payload" in captured.err
