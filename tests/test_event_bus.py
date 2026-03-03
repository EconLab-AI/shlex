import asyncio
import pytest

from core.event_bus import EventBus
from core.models import Event, EventType


@pytest.fixture
def bus():
    return EventBus()


async def test_subscribe_and_publish(bus):
    received = []

    async def handler(event: Event):
        received.append(event)

    bus.subscribe(EventType.TASK_NEW, handler)
    event = Event(event_type=EventType.TASK_NEW, payload={"title": "test"})
    await bus.publish(event)
    await asyncio.sleep(0.05)
    assert len(received) == 1
    assert received[0].payload["title"] == "test"


async def test_multiple_subscribers(bus):
    count = {"a": 0, "b": 0}

    async def handler_a(event: Event):
        count["a"] += 1

    async def handler_b(event: Event):
        count["b"] += 1

    bus.subscribe(EventType.TASK_NEW, handler_a)
    bus.subscribe(EventType.TASK_NEW, handler_b)
    await bus.publish(Event(event_type=EventType.TASK_NEW))
    await asyncio.sleep(0.05)
    assert count["a"] == 1
    assert count["b"] == 1


async def test_wildcard_subscriber(bus):
    received = []

    async def handler(event: Event):
        received.append(event)

    bus.subscribe_all(handler)
    await bus.publish(Event(event_type=EventType.TASK_NEW))
    await bus.publish(Event(event_type=EventType.ERROR))
    await asyncio.sleep(0.05)
    assert len(received) == 2


async def test_no_crosstalk(bus):
    received = []

    async def handler(event: Event):
        received.append(event)

    bus.subscribe(EventType.TASK_NEW, handler)
    await bus.publish(Event(event_type=EventType.ERROR))
    await asyncio.sleep(0.05)
    assert len(received) == 0
