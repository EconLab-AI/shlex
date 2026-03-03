from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


class OutputSignal(str, Enum):
    QUESTION = "question"
    ERROR = "error"
    TASK_DONE = "task_done"
    PERMISSION = "permission"
    IDLE = "idle"
    WORKING = "working"


@dataclass
class ParseResult:
    signals: list[OutputSignal] = field(default_factory=list)
    last_message: str = ""
    raw: str = ""


_QUESTION_PATTERNS = [
    r"which .+ (?:do you|should|would you)",
    r"\?\s*$",
    r"(?:choose|select|pick) (?:one|an option|from)",
    r"(?:option [a-d]|1\.|2\.|3\.)",
]

_ERROR_PATTERNS = [
    r"^Error:",
    r"(?:ModuleNotFoundError|ImportError|TypeError|ValueError|SyntaxError|RuntimeError):",
    r"Traceback \(most recent call last\)",
    r"^FAILED ",
    r"panic:",
]

_DONE_PATTERNS = [
    r"(?:feature|task|implementation) (?:is )?(?:now )?(?:complete|done|finished)",
    r"all tests pass",
    r"successfully committed",
    r"committed as [a-f0-9]",
]

_PERMISSION_PATTERNS = [
    r"(?:do you )?want to allow",
    r"\(y/n\)",
    r"allow this (?:action|tool|operation)",
]

_IDLE_PATTERNS = [
    r"^\$\s*$",
    r"^>\s*$",
    r"^claude\s*>\s*$",
]


class OutputParser:
    def parse(self, raw_output: str) -> ParseResult:
        result = ParseResult(raw=raw_output)
        lines = raw_output.strip().split("\n")
        result.last_message = lines[-1].strip() if lines else ""
        lower = raw_output.lower()

        if _any_match(_IDLE_PATTERNS, raw_output.strip()):
            result.signals.append(OutputSignal.IDLE)
            return result

        if _any_match(_PERMISSION_PATTERNS, lower):
            result.signals.append(OutputSignal.PERMISSION)

        if _any_match(_ERROR_PATTERNS, raw_output):
            result.signals.append(OutputSignal.ERROR)

        if _any_match(_QUESTION_PATTERNS, lower):
            result.signals.append(OutputSignal.QUESTION)

        if _any_match(_DONE_PATTERNS, lower):
            result.signals.append(OutputSignal.TASK_DONE)

        if not result.signals:
            result.signals.append(OutputSignal.WORKING)

        return result


def _any_match(patterns: list[str], text: str) -> bool:
    return any(re.search(p, text, re.MULTILINE | re.IGNORECASE) for p in patterns)
