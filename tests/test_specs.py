import pytest
from agy_route.specs.command_specs import (
    COMMAND_SPECS,
    RESEARCH_FETCH_PROMPT_PREFIX,
    RESEARCH_QUOTE_PROMPT_TEMPLATE,
    CommandSpec,
)


def test_command_specs_loaded():
    assert len(COMMAND_SPECS) >= 2
    names = [spec.name for spec in COMMAND_SPECS]
    assert "agy-web-search" in names
    assert "agy-research" in names


def test_command_spec_post_init_autoload():
    spec = CommandSpec(name="agy-web-search", description="test description")
    assert spec.body != ""
    assert "agy-web-search" in spec.body or "agy" in spec.body


def test_render_claude():
    spec = CommandSpec(
        name="test-cmd",
        description="Test description",
        argument_hint="<query>",
        body="Body content here",
    )
    rendered = spec.render_claude()
    assert "---" in rendered
    assert 'description: "Test description"' in rendered
    assert 'argument-hint: "<query>"' in rendered
    assert "Body content here" in rendered


def test_render_opencode():
    spec = CommandSpec(
        name="test-cmd",
        description="Test description",
        opencode_agent="researcher",
        opencode_model="gemini",
        opencode_subtask=True,
        body="Body content here",
    )
    rendered = spec.render_opencode()
    assert "---" in rendered
    assert 'description: "Test description"' in rendered
    assert "agent: researcher" in rendered
    assert "model: gemini" in rendered
    assert "subtask: true" in rendered
    assert "Body content here" in rendered


def test_prompt_constants():
    assert "Sub-question:" in RESEARCH_FETCH_PROMPT_PREFIX
    formatted = RESEARCH_QUOTE_PROMPT_TEMPLATE.format(url="https://example.com", claim="test claim")
    assert "https://example.com" in formatted
    assert "test claim" in formatted


def test_static_claude_commands_in_sync():
    from pathlib import Path
    repo_root = Path(__file__).resolve().parent.parent
    claude_cmds_dir = repo_root / "plugins" / "claude" / "commands"
    assert claude_cmds_dir.is_dir()

    for spec in COMMAND_SPECS:
        cmd_file = claude_cmds_dir / f"{spec.name}.md"
        assert cmd_file.is_file(), f"Missing static command file {cmd_file}"
        assert cmd_file.read_text() == spec.render_claude(), (
            f"Static command file {cmd_file} is out of sync with COMMAND_SPECS. "
            "Run 'uv run python tools/generate_commands.py' to update."
        )

