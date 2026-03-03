import pytest

from execution.output_parser import OutputParser, OutputSignal


def test_detect_question():
    parser = OutputParser()
    result = parser.parse("Which approach do you prefer?\n1. Option A\n2. Option B")
    assert OutputSignal.QUESTION in result.signals


def test_detect_error():
    parser = OutputParser()
    result = parser.parse("Error: ModuleNotFoundError: No module named 'foo'")
    assert OutputSignal.ERROR in result.signals


def test_detect_task_complete():
    parser = OutputParser()
    result = parser.parse("All tests passed. The feature is now complete and committed.")
    assert OutputSignal.TASK_DONE in result.signals


def test_detect_permission_request():
    parser = OutputParser()
    result = parser.parse("Do you want to allow this action? (y/n)")
    assert OutputSignal.PERMISSION in result.signals


def test_detect_idle():
    parser = OutputParser()
    result = parser.parse("$ ")
    assert OutputSignal.IDLE in result.signals


def test_extract_last_message():
    parser = OutputParser()
    output = "Some earlier output\n\nHere is my final answer about the implementation."
    result = parser.parse(output)
    assert "final answer" in result.last_message


def test_no_false_positives():
    parser = OutputParser()
    result = parser.parse("Writing the function to handle errors gracefully")
    assert OutputSignal.ERROR not in result.signals
    assert OutputSignal.QUESTION not in result.signals
