from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Mapping


@dataclass(frozen=True)
class RuntimeEvent:
    event_type: str
    workflow_id: str
    run_id: str
    payload: Mapping[str, Any] = field(default_factory=dict)
    occurred_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


EventHandler = Callable[[RuntimeEvent], None]


class EventBus:
    """Small synchronous event bus for runtime lifecycle events.

    Providers may replace this implementation later with a durable transport,
    while the Workflow runtime keeps depending on the same publish/subscribe
    contract.
    """

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = {}
        self._history: list[RuntimeEvent] = []

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        handlers = self._handlers.setdefault(event_type, [])
        if handler not in handlers:
            handlers.append(handler)

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        handlers = self._handlers.get(event_type, [])
        if handler in handlers:
            handlers.remove(handler)

    def publish(self, event: RuntimeEvent) -> None:
        self._history.append(event)
        for handler in tuple(self._handlers.get(event.event_type, ())):
            handler(event)
        for handler in tuple(self._handlers.get("*", ())):
            handler(event)

    @property
    def history(self) -> tuple[RuntimeEvent, ...]:
        return tuple(self._history)
