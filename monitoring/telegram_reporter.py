from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class TelegramReporter:
    def __init__(self, bot, chat_id: int) -> None:
        self._bot = bot
        self._chat_id = chat_id

    async def send_task_started(self, title: str, strategy: str, estimate: str = "") -> None:
        est = f", ~{estimate}" if estimate else ""
        await self._send(f"Task gestartet: {title} ({strategy.upper()}{est})")

    async def send_progress(self, title: str, details: str) -> None:
        await self._send(f"Fortschritt: {title}\n{details}")

    async def send_error(self, error: str, session: str = "") -> None:
        ctx = f" in {session}" if session else ""
        await self._send(f"FEHLER{ctx}:\n{error}")

    async def send_decision_request(self, question: str, options: list[str] | None = None) -> None:
        msg = f"Entscheidung noetig:\n{question}"
        if options:
            opts = " | ".join(f"[{o}]" for o in options)
            msg += f"\n\nOptionen: {opts}"
        msg += "\n\n/approve oder /reject <grund>"
        await self._send(msg)

    async def send_task_complete(self, title: str, summary: str) -> None:
        await self._send(f"FERTIG: {title}\n{summary}")

    async def send_reflection(self, summary: str) -> None:
        await self._send(f"Session-Reflexion:\n{summary}")

    async def _send(self, text: str) -> None:
        try:
            await self._bot.send_message(chat_id=self._chat_id, text=text)
        except Exception as e:
            logger.error("Failed to send Telegram message: %s", e)
