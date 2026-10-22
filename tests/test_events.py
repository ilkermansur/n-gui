"""test_events.py - app/core/events.py için testler."""

from app.core.events import EventBus


def test_publish_calls_handlers_in_order():
    """Handler'lar abone olma sırasıyla çağrılmalı."""
    bus = EventBus()
    calls = []

    def first(data):
        calls.append("first")

    def second(data):
        calls.append("second")

    bus.subscribe("x", first)
    bus.subscribe("x", second)
    bus.publish("x", {})
    assert calls == ["first", "second"]


def test_failing_handler_does_not_stop_others():
    """İlk handler hata verse de ikincisi çağrılmalı, publish hata atmamalı."""
    bus = EventBus()
    calls = []

    def broken(data):
        raise RuntimeError("bozuk")

    def working(data):
        calls.append("working")

    bus.subscribe("x", broken)
    bus.subscribe("x", working)
    bus.publish("x", {})
    assert calls == ["working"]
