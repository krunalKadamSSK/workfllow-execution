from __future__ import annotations

from collections import defaultdict

from app.domain.events.stored_event import StoredEvent
from app.domain.ports.events import EventHandler


class EventHandlerRegistry:
    """Observer registry dispatching events to subscribed handlers."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)

    def register(self, handler: EventHandler) -> None:
        for event_type in handler.handles():
            self._handlers[event_type].append(handler)

    def dispatch(self, event: StoredEvent) -> None:
        for handler in self._handlers.get(event.event_type, []):
            handler.handle(event)

    def registered_event_types(self) -> frozenset[str]:
        return frozenset(self._handlers)
