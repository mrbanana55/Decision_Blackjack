"""Unit tests for simulation event broadcasting and EventEmitter."""

import asyncio
from app.simulation.events import EventEmitter, EventType, SimulationEvent
from app.simulation.interfaces import EventPublisher


def test_event_emitter_implements_protocol():
    emitter = EventEmitter()
    assert isinstance(emitter, EventPublisher)


def test_event_creation_and_fields():
    evt = SimulationEvent(
        session_id="sim-test-1",
        event_type=EventType.SESSION_STARTED,
        payload={"seed": 42, "tables": ["jev", "laya"]},
    )
    assert evt.session_id == "sim-test-1"
    assert evt.event_type == EventType.SESSION_STARTED
    assert evt.event_type == "session_started"
    assert evt.payload["seed"] == 42
    assert evt.event_id.startswith("evt-")
    assert evt.timestamp is not None


def test_sync_listener_dispatch():
    async def _test():
        emitter = EventEmitter()
        received = []

        def on_started(event: SimulationEvent):
            received.append(event)

        emitter.subscribe(EventType.SESSION_STARTED, on_started)

        evt1 = SimulationEvent("sim-1", EventType.SESSION_STARTED, {"data": 1})
        evt2 = SimulationEvent("sim-1", EventType.ROUND_STARTED, {"round": 1})

        await emitter.emit(evt1)
        await emitter.emit(evt2)

        assert len(received) == 1
        assert received[0].payload["data"] == 1
        assert len(emitter.history) == 2

    asyncio.run(_test())


def test_async_listener_dispatch():
    async def _test():
        emitter = EventEmitter()
        received = []

        async def on_round(event: SimulationEvent):
            await asyncio.sleep(0.001)
            received.append(event.payload["round"])

        emitter.subscribe(EventType.ROUND_STARTED, on_round)

        await emitter.emit(SimulationEvent("sim-1", EventType.ROUND_STARTED, {"round": 1}))
        await emitter.emit(SimulationEvent("sim-1", EventType.ROUND_STARTED, {"round": 2}))

        assert received == [1, 2]

    asyncio.run(_test())


def test_wildcard_subscription_receives_all_events():
    async def _test():
        emitter = EventEmitter()
        all_events = []

        emitter.subscribe(None, lambda e: all_events.append(e.event_type))

        await emitter.emit(SimulationEvent("sim-1", EventType.SESSION_STARTED))
        await emitter.emit(SimulationEvent("sim-1", EventType.ROUND_STARTED))
        await emitter.emit(SimulationEvent("sim-1", EventType.DECISION_APPLIED))
        await emitter.emit(SimulationEvent("sim-1", EventType.SESSION_COMPLETED))

        assert all_events == [
            EventType.SESSION_STARTED,
            EventType.ROUND_STARTED,
            EventType.DECISION_APPLIED,
            EventType.SESSION_COMPLETED,
        ]

    asyncio.run(_test())


def test_chronological_ordering():
    async def _test():
        emitter = EventEmitter()
        dispatched_order = []

        emitter.subscribe(None, lambda e: dispatched_order.append(e.payload["seq"]))

        for i in range(10):
            await emitter.emit(SimulationEvent("sim-1", EventType.CARD_DEALT, {"seq": i}))

        assert dispatched_order == list(range(10))
        assert [e.payload["seq"] for e in emitter.history] == list(range(10))

    asyncio.run(_test())


def test_listener_exception_isolation():
    async def _test():
        emitter = EventEmitter()
        survived = []

        def failing_listener(e: SimulationEvent):
            raise RuntimeError("Boom!")

        def healthy_listener(e: SimulationEvent):
            survived.append(e.event_type)

        emitter.subscribe(EventType.SESSION_STARTED, failing_listener)
        emitter.subscribe(EventType.SESSION_STARTED, healthy_listener)

        evt = SimulationEvent("sim-1", EventType.SESSION_STARTED)
        await emitter.emit(evt)

        # The healthy listener still ran despite the exception in the first listener
        assert survived == [EventType.SESSION_STARTED]

    asyncio.run(_test())


def test_unsubscribe():
    async def _test():
        emitter = EventEmitter()
        received = []

        def listener(e: SimulationEvent):
            received.append(e)

        emitter.subscribe(EventType.ROUND_STARTED, listener)
        await emitter.emit(SimulationEvent("sim-1", EventType.ROUND_STARTED))
        assert len(received) == 1

        emitter.unsubscribe(EventType.ROUND_STARTED, listener)
        await emitter.emit(SimulationEvent("sim-1", EventType.ROUND_STARTED))
        assert len(received) == 1

    asyncio.run(_test())


if __name__ == "__main__":
    for name, func in list(globals().items()):
        if name.startswith("test_") and callable(func):
            func()
            print(f"✓ {name}")
    print("All event tests passed!")
