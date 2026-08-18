from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from src.shared.events.domain_events import DomainEvent, DomainEventName


@dataclass(frozen=True)
class EventEnvelope:
    name: DomainEventName
    aggregate_type: str
    aggregate_id: UUID
    payload: dict[str, Any]


EventHandler = Callable[[EventEnvelope], None]


class InProcessEventBus:
    def __init__(self, session: Session) -> None:
        self.session = session
        self._handlers: dict[DomainEventName, list[EventHandler]] = {}

    def subscribe(self, event_name: DomainEventName, handler: EventHandler) -> None:
        self._handlers.setdefault(event_name, []).append(handler)

    def publish(self, envelope: EventEnvelope) -> DomainEvent:
        event = DomainEvent(
            name=envelope.name,
            aggregate_type=envelope.aggregate_type,
            aggregate_id=envelope.aggregate_id,
            payload=envelope.payload,
        )
        self.session.add(event)
        for handler in self._handlers.get(envelope.name, []):
            handler(envelope)
        return event
