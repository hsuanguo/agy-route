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
        assert "installed:" in result.stdout
        assert "skill →" in result.stdout
        assert "plugin → opencode" in result.stdout
        assert "commands →" in result.stdout


def test_uninstall_cmd_scan_all(tmp_path):
    with patch("pathlib.Path.home", return_value=tmp_path):
        # Install first
        runner.invoke(app, ["install", "--target", "claude"])
        # Uninstall all
        result = runner.invoke(app, ["uninstall"])
        assert result.exit_code == 0
        assert "claude:" in result.stdout
