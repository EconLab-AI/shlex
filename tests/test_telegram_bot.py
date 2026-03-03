
from input.telegram_bot import TelegramInput, parse_command


def test_parse_status_command():
    cmd, args = parse_command("/status")
    assert cmd == "status"
    assert args == ""


def test_parse_stop_command_with_args():
    cmd, args = parse_command("/stop task-123")
    assert cmd == "stop"
    assert args == "task-123"


def test_parse_regular_text():
    cmd, args = parse_command("Build me a login page")
    assert cmd is None
    assert args == "Build me a login page"


def test_parse_approve():
    cmd, args = parse_command("/approve")
    assert cmd == "approve"


def test_allowed_user_check():
    bot = TelegramInput(token="fake", allowed_users=[123, 456])
    assert bot.is_allowed(123) is True
    assert bot.is_allowed(789) is False


def test_empty_allowed_users_allows_all():
    bot = TelegramInput(token="fake", allowed_users=[])
    assert bot.is_allowed(999) is True
