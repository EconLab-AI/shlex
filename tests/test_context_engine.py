# tests/test_context_engine.py
import pytest
import os

from brain.context_engine import ContextEngine


@pytest.fixture
def project_dir(tmp_path):
    """Create a fake project directory."""
    (tmp_path / "CLAUDE.md").write_text("# Rules\n- Use pytest\n- No console.log")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("print('hello')")
    (tmp_path / ".git").mkdir()
    return str(tmp_path)


@pytest.fixture
def engine(project_dir):
    return ContextEngine(project_dir)


async def test_load_claude_md(engine, project_dir):
    ctx = await engine.load_context()
    assert "Use pytest" in ctx.claude_md


async def test_load_file_structure(engine):
    ctx = await engine.load_context()
    assert any("main.py" in f for f in ctx.file_structure)


async def test_context_to_string(engine):
    ctx = await engine.load_context()
    text = ctx.to_prompt_section()
    assert "# Projektkontext" in text
    assert "CLAUDE.md" in text


async def test_no_claude_md_still_works(tmp_path):
    engine = ContextEngine(str(tmp_path))
    ctx = await engine.load_context()
    assert ctx.claude_md == ""
