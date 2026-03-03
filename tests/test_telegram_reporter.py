# tests/test_telegram_reporter.py
import pytest
from unittest.mock import AsyncMock

from monitoring.telegram_reporter import TelegramReporter


@pytest.fixture
def reporter():
    bot = AsyncMock()
    return TelegramReporter(bot=bot, chat_id=12345)


async def test_send_task_started(reporter):
    await reporter.send_task_started("Login Feature", "parallel", "~15min")
    reporter._bot.send_message.assert_called_once()
    msg = reporter._bot.send_message.call_args[1]["text"]
    assert "Login Feature" in msg


async def test_send_progress(reporter):
    await reporter.send_progress("Login Feature", "Frontend done, Backend 70%")
    reporter._bot.send_message.assert_called_once()


async def test_send_error(reporter):
    await reporter.send_error("test_auth failed", "Backend Session")
    reporter._bot.send_message.assert_called_once()
    msg = reporter._bot.send_message.call_args[1]["text"]
    assert "test_auth" in msg


async def test_send_decision_request(reporter):
    await reporter.send_decision_request(
        "Auth-Strategie: JWT oder Session-based?",
        options=["JWT", "Session-based"],
    )
    reporter._bot.send_message.assert_called_once()


async def test_send_task_complete(reporter):
    await reporter.send_task_complete("Login Feature", "6 Files, Tests gruen, abc123")
    reporter._bot.send_message.assert_called_once()
