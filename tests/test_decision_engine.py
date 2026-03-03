# tests/test_decision_engine.py
import pytest

from execution.decision_engine import DecisionEngine, DecisionType
from execution.output_parser import ParseResult, OutputSignal


@pytest.fixture
def engine():
    return DecisionEngine()


def test_working_continues(engine):
    parse = ParseResult(signals=[OutputSignal.WORKING])
    decision = engine.decide(parse)
    assert decision.type == DecisionType.CONTINUE


def test_error_retries(engine):
    parse = ParseResult(signals=[OutputSignal.ERROR], raw="Error: test failure")
    decision = engine.decide(parse)
    assert decision.type == DecisionType.RETRY


def test_permission_auto_approves(engine):
    parse = ParseResult(signals=[OutputSignal.PERMISSION])
    decision = engine.decide(parse)
    assert decision.type == DecisionType.AUTO_APPROVE


def test_question_escalates(engine):
    parse = ParseResult(signals=[OutputSignal.QUESTION], raw="Which approach?")
    decision = engine.decide(parse)
    assert decision.type == DecisionType.ESCALATE


def test_done_completes(engine):
    parse = ParseResult(signals=[OutputSignal.TASK_DONE])
    decision = engine.decide(parse)
    assert decision.type == DecisionType.COMPLETE


def test_repeated_errors_escalate(engine):
    parse = ParseResult(signals=[OutputSignal.ERROR], raw="Same error again")
    engine.decide(parse)  # First: retry
    engine.decide(parse)  # Second: retry
    decision = engine.decide(parse)  # Third: escalate
    assert decision.type == DecisionType.ESCALATE
