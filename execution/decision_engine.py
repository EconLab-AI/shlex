# execution/decision_engine.py
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from execution.output_parser import ParseResult, OutputSignal


class DecisionType(str, Enum):
    CONTINUE = "continue"
    RETRY = "retry"
    AUTO_APPROVE = "auto_approve"
    ESCALATE = "escalate"
    COMPLETE = "complete"


@dataclass
class Decision:
    type: DecisionType
    message: str = ""
    followup_prompt: str = ""


class DecisionEngine:
    def __init__(self, max_retries: int = 2) -> None:
        self._max_retries = max_retries
        self._error_count = 0

    def decide(self, parse_result: ParseResult) -> Decision:
        signals = parse_result.signals

        if OutputSignal.TASK_DONE in signals:
            self._error_count = 0
            return Decision(type=DecisionType.COMPLETE, message="Task completed")

        if OutputSignal.PERMISSION in signals:
            return Decision(
                type=DecisionType.AUTO_APPROVE,
                message="Auto-approving permission",
                followup_prompt="y",
            )

        if OutputSignal.ERROR in signals:
            self._error_count += 1
            if self._error_count > self._max_retries:
                return Decision(
                    type=DecisionType.ESCALATE,
                    message=f"Error repeated {self._error_count} times, escalating",
                )
            return Decision(
                type=DecisionType.RETRY,
                message=f"Error detected (attempt {self._error_count}), retrying",
                followup_prompt="The previous attempt had an error. Please analyze the root cause and try again.",
            )

        if OutputSignal.QUESTION in signals:
            return Decision(
                type=DecisionType.ESCALATE,
                message="Claude is asking a question",
            )

        if OutputSignal.IDLE in signals:
            return Decision(type=DecisionType.CONTINUE, message="Session idle")

        return Decision(type=DecisionType.CONTINUE, message="Working...")

    def reset(self) -> None:
        self._error_count = 0
