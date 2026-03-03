# tests/test_prompt_generator.py
import pytest

from brain.prompt_generator import PromptGenerator
from brain.context_engine import ProjectContext


@pytest.fixture
def generator():
    return PromptGenerator()


@pytest.fixture
def sample_context():
    return ProjectContext(
        claude_md="# Rules\n- Use pytest",
        git_log="abc123 last commit",
        git_status="M src/main.py",
        file_structure=["src/main.py", "tests/test_main.py"],
        error_memories=["Route /users missing auth middleware"],
    )


def test_generate_feature_prompt(generator, sample_context):
    prompt = generator.generate(
        task_type="feature",
        user_input="Add user login",
        context=sample_context,
        complexity="medium",
    )
    assert "Add user login" in prompt
    assert "Projektkontext" in prompt
    assert "Use pytest" in prompt
    assert "NICHT WIEDERHOLEN" in prompt


def test_generate_bugfix_prompt(generator, sample_context):
    prompt = generator.generate(
        task_type="bugfix",
        user_input="Fix login crash",
        context=sample_context,
        complexity="simple",
    )
    assert "Fix login crash" in prompt
    assert "Root-Cause" in prompt


def test_ultrathink_for_complex(generator, sample_context):
    prompt = generator.generate(
        task_type="feature",
        user_input="Refactor auth system",
        context=sample_context,
        complexity="complex",
    )
    assert "ultrathink" in prompt.lower() or "Ultrathink" in prompt


def test_team_mode_for_complex(generator, sample_context):
    prompt = generator.generate(
        task_type="feature",
        user_input="Build full stack feature",
        context=sample_context,
        complexity="complex",
    )
    assert "Team" in prompt or "tmux" in prompt


def test_quality_gates_always_present(generator, sample_context):
    prompt = generator.generate(
        task_type="feature",
        user_input="Simple thing",
        context=sample_context,
        complexity="simple",
    )
    assert "Checkpoint" in prompt or "checkpoint" in prompt


def test_reflection_always_present(generator, sample_context):
    prompt = generator.generate(
        task_type="feature",
        user_input="Simple thing",
        context=sample_context,
        complexity="simple",
    )
    assert "Reflexion" in prompt or "reflekt" in prompt.lower()
