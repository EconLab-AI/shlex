# brain/task_planner.py
from __future__ import annotations

import re
from dataclasses import dataclass, field

from core.models import TaskStrategy

_BUGFIX_KEYWORDS = ["fix", "bug", "crash", "error", "broken", "failing", "issue"]
_REFACTOR_KEYWORDS = ["refactor", "restructure", "reorganize", "clean up", "migrate"]
_RESEARCH_KEYWORDS = ["research", "investigate", "explore", "compare", "evaluate"]

_COMPLEXITY_MARKERS_HIGH = [
    "entire", "all", "complete", "full", "system", "architecture",
    "migrate", "rebuild",
]
_COMPLEXITY_MARKERS_MEDIUM = [
    "frontend and backend", "with api", "multiple", "both", "and backend",
    "with tests", "and tests",
]
_PARALLEL_INDICATORS = [
    "frontend and backend", "client and server", "ui and api",
    "with tests",
]


@dataclass
class PlanResult:
    strategy: TaskStrategy
    complexity: str  # simple, medium, complex
    task_type: str  # feature, bugfix, refactor, research
    subtasks: list[str] = field(default_factory=list)
    recommended_skills: list[str] = field(default_factory=list)


class TaskPlanner:
    def analyze(self, user_input: str) -> PlanResult:
        lower = user_input.lower()
        task_type = self._detect_type(lower)
        complexity = self._assess_complexity(lower)
        strategy = self._choose_strategy(lower, complexity)
        subtasks = self._extract_subtasks(lower, strategy)
        skills = self._recommend_skills(task_type)

        return PlanResult(
            strategy=strategy,
            complexity=complexity,
            task_type=task_type,
            subtasks=subtasks,
            recommended_skills=skills,
        )

    def _detect_type(self, text: str) -> str:
        if any(kw in text for kw in _BUGFIX_KEYWORDS):
            return "bugfix"
        if any(kw in text for kw in _REFACTOR_KEYWORDS):
            return "refactor"
        if any(kw in text for kw in _RESEARCH_KEYWORDS):
            return "research"
        return "feature"

    def _assess_complexity(self, text: str) -> str:
        word_count = len(text.split())
        high_markers = sum(1 for m in _COMPLEXITY_MARKERS_HIGH if m in text)
        med_markers = sum(1 for m in _COMPLEXITY_MARKERS_MEDIUM if m in text)

        if high_markers >= 2 or word_count > 40:
            return "complex"
        if med_markers >= 1 or word_count > 15:
            return "medium"
        return "simple"

    def _choose_strategy(self, text: str, complexity: str) -> TaskStrategy:
        if complexity == "complex":
            return TaskStrategy.HIERARCHICAL
        if any(ind in text for ind in _PARALLEL_INDICATORS):
            return TaskStrategy.PARALLEL
        if complexity == "medium":
            return TaskStrategy.PARALLEL
        return TaskStrategy.SERIAL

    def _extract_subtasks(self, text: str, strategy: TaskStrategy) -> list[str]:
        if strategy == TaskStrategy.SERIAL:
            return []
        parts = re.split(r",\s*(?:and\s+)?|(?:\s+and\s+)", text)
        return [p.strip() for p in parts if len(p.strip()) > 5]

    def _recommend_skills(self, task_type: str) -> list[str]:
        mapping = {
            "feature": ["brainstorming", "writing-plans", "test-driven-development"],
            "bugfix": ["systematic-debugging", "root-cause-tracing"],
            "refactor": ["test-driven-development", "writing-plans"],
            "research": [],
        }
        return mapping.get(task_type, [])
