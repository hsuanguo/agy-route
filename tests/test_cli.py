from unittest.mock import patch
from typer.testing import CliRunner

from agy_route.cli import app

runner = CliRunner()


def test_types_cmd():
    result = runner.invoke(app, ["types"])
    assert result.exit_code == 0
    assert "search" in result.stdout
    assert "gemini" in result.stdout


def test_targets_cmd():
    result = runner.invoke(app, ["targets"])
    assert result.exit_code == 0
    assert "claude" in result.stdout
    assert "opencode" in result.stdout


def test_install_cmd_dry_run():
    result = runner.invoke(app, ["install", "--target", "claude", "--dry-run"])
    assert result.exit_code == 0
    assert "[dry-run]" in result.stdout


def test_install_cmd_opencode_output_paths(tmp_path):
    with patch("pathlib.Path.home", return_value=tmp_path):
        result = runner.invoke(app, ["install", "--target", "opencode"])
        assert result.exit_code == 0
        assert "installed (opencode):" in result.stdout
        assert "• skills:" in result.stdout
        assert "• commands:" in result.stdout

        # With plugin/hook flag
        res_with = runner.invoke(app, ["install", "--target", "opencode", "--with-plugin"])
        assert res_with.exit_code == 0
        assert "• plugin:" in res_with.stdout


def test_install_cmd_mutually_exclusive_flags():
    result = runner.invoke(app, ["install", "--with-hook", "--only-skill"])
    assert result.exit_code != 0
    assert "mutually exclusive" in result.stderr or "mutually exclusive" in result.stdout


def test_install_cmd_invalid_target():
    result = runner.invoke(app, ["install", "--target", "nonexistent"])
    assert result.exit_code != 0
    assert "unknown target" in result.stderr or "unknown target" in result.stdout


def test_uninstall_cmd_scan_all(tmp_path):
    with patch("pathlib.Path.home", return_value=tmp_path):
        # Install first
        runner.invoke(app, ["install", "--target", "claude"])
        # Uninstall all
        result = runner.invoke(app, ["uninstall"])
        assert result.exit_code == 0
        assert "claude:" in result.stdout
