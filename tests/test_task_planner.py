# tests/test_task_planner.py
import pytest

from brain.task_planner import TaskPlanner
from core.models import TaskStrategy


@pytest.fixture
def planner():
    return TaskPlanner()


def test_simple_task_serial(planner):
    result = planner.analyze("Fix the typo in README")
    assert result.strategy == TaskStrategy.SERIAL
    assert result.complexity == "simple"


def test_medium_task_parallel(planner):
    result = planner.analyze("Build login page with frontend and backend API")
    assert result.strategy == TaskStrategy.PARALLEL
    assert result.complexity == "medium"


def test_complex_task_hierarchical(planner):
    result = planner.analyze(
        "Refactor the entire authentication system: update database schema, "
        "migrate API endpoints, rebuild frontend components, update all tests, "
        "and add monitoring"
    )
    assert result.strategy == TaskStrategy.HIERARCHICAL
    assert result.complexity == "complex"


def test_subtask_generation(planner):
    result = planner.analyze("Build login with frontend form and backend API")
    assert len(result.subtasks) >= 2


def test_task_type_detection_bugfix(planner):
    result = planner.analyze("Fix the crash when user clicks login button")
    assert result.task_type == "bugfix"


def test_task_type_detection_feature(planner):
    result = planner.analyze("Add a dark mode toggle to the settings page")
    assert result.task_type == "feature"
