from __future__ import annotations

import logging

from core.database import Database
from core.event_bus import EventBus
from core.models import Event

logger = logging.getLogger(__name__)


class EventLogger:
    def __init__(self, db: Database, event_bus: EventBus) -> None:
        self._db = db
        self._bus = event_bus

    def start(self) -> None:
        self._bus.subscribe_all(self._log_event)

    async def _log_event(self, event: Event) -> None:
        try:
            await self._db.save_event(event)
        except Exception:
            logger.exception("Failed to log event")
