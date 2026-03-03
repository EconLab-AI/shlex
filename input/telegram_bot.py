from __future__ import annotations

import logging

from core.event_bus import EventBus
from core.models import Event, EventType

logger = logging.getLogger(__name__)


def parse_command(text: str) -> tuple[str | None, str]:
    text = text.strip()
    if text.startswith("/"):
        parts = text[1:].split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        return cmd, args
    return None, text


class TelegramInput:
    def __init__(
        self,
        token: str,
        allowed_users: list[int] | None = None,
        event_bus: EventBus | None = None,
    ) -> None:
        self._token = token
        self._allowed_users = allowed_users or []
        self._bus = event_bus

    def is_allowed(self, user_id: int) -> bool:
        if not self._allowed_users:
            return True
        return user_id in self._allowed_users

    async def start(self) -> None:
        from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters

        app = ApplicationBuilder().token(self._token).build()
        app.add_handler(CommandHandler("status", self._handle_status))
        app.add_handler(CommandHandler("sessions", self._handle_sessions))
        app.add_handler(CommandHandler("stop", self._handle_stop))
        app.add_handler(CommandHandler("pause", self._handle_pause))
        app.add_handler(CommandHandler("resume", self._handle_resume))
        app.add_handler(CommandHandler("approve", self._handle_approve))
        app.add_handler(CommandHandler("reject", self._handle_reject))
        app.add_handler(CommandHandler("logs", self._handle_logs))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_text))
        app.add_handler(MessageHandler(filters.VOICE, self._handle_voice))
        app.add_handler(MessageHandler(filters.Document.ALL, self._handle_document))

        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        self._app = app

    async def stop(self) -> None:
        if hasattr(self, "_app"):
            await self._app.updater.stop()
            await self._app.stop()
            await self._app.shutdown()

    async def _check_auth(self, update) -> bool:
        user_id = update.effective_user.id
        if not self.is_allowed(user_id):
            await update.message.reply_text("Unauthorized.")
            return False
        return True

    async def _handle_text(self, update, context) -> None:
        if not await self._check_auth(update):
            return
        text = update.message.text
        if self._bus:
            await self._bus.publish(Event(
                event_type=EventType.TASK_NEW,
                payload={
                    "raw_input": text,
                    "source": "telegram",
                    "chat_id": update.effective_chat.id,
                },
            ))
        await update.message.reply_text("Task received. Processing...")

    async def _handle_voice(self, update, context) -> None:
        if not await self._check_auth(update):
            return
        voice = update.message.voice
        file = await context.bot.get_file(voice.file_id)
        path = f"/tmp/voice_{voice.file_id}.ogg"
        await file.download_to_drive(path)
        if self._bus:
            await self._bus.publish(Event(
                event_type=EventType.TASK_NEW,
                payload={
                    "voice_path": path,
                    "source": "telegram_voice",
                    "chat_id": update.effective_chat.id,
                },
            ))
        await update.message.reply_text("Voice message received. Transcribing...")

    async def _handle_document(self, update, context) -> None:
        if not await self._check_auth(update):
            return
        doc = update.message.document
        file = await context.bot.get_file(doc.file_id)
        path = f"/tmp/doc_{doc.file_id}_{doc.file_name}"
        await file.download_to_drive(path)
        caption = update.message.caption or ""
        if self._bus:
            await self._bus.publish(Event(
                event_type=EventType.TASK_NEW,
                payload={
                    "file_path": path,
                    "caption": caption,
                    "source": "telegram_file",
                    "chat_id": update.effective_chat.id,
                },
            ))
        await update.message.reply_text(f"File '{doc.file_name}' received.")

    async def _handle_status(self, update, context) -> None:
        if not await self._check_auth(update):
            return
        await update.message.reply_text("Fetching status...")

    async def _handle_sessions(self, update, context) -> None:
        if not await self._check_auth(update):
            return
        await update.message.reply_text("Fetching sessions...")

    async def _handle_stop(self, update, context) -> None:
        if not await self._check_auth(update):
            return
        args = " ".join(context.args) if context.args else ""
        await update.message.reply_text(f"Stopping: {args}")

    async def _handle_pause(self, update, context) -> None:
        if not await self._check_auth(update):
            return
        await update.message.reply_text("Pausing all sessions...")

    async def _handle_resume(self, update, context) -> None:
        if not await self._check_auth(update):
            return
        await update.message.reply_text("Resuming...")

    async def _handle_approve(self, update, context) -> None:
        if not await self._check_auth(update):
            return
        if self._bus:
            await self._bus.publish(Event(
                event_type=EventType.DECISION_MADE,
                payload={"decision": "approve", "source": "telegram"},
            ))
        await update.message.reply_text("Approved.")

    async def _handle_reject(self, update, context) -> None:
        if not await self._check_auth(update):
            return
        reason = " ".join(context.args) if context.args else "No reason given"
        if self._bus:
            await self._bus.publish(Event(
                event_type=EventType.DECISION_MADE,
                payload={"decision": "reject", "reason": reason, "source": "telegram"},
            ))
        await update.message.reply_text(f"Rejected: {reason}")

    async def _handle_logs(self, update, context) -> None:
        if not await self._check_auth(update):
            return
        await update.message.reply_text("Fetching logs...")
