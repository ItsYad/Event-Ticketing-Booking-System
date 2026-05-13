from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List
from uuid import UUID, uuid4
import secrets
import string

from src.domain.events.domain_events import DomainEvent, TicketCheckedIn


# ── Enum ──────────────────────────────────────────────────────────────────────

class TicketStatus(Enum):
    ACTIVE = "Active"
    CHECKED_IN = "CheckedIn"
    CANCELLED = "Cancelled"


# ── Aggregate Root: Ticket ────────────────────────────────────────────────────

@dataclass
class Ticket:
    id: UUID
    booking_id: UUID
    customer_id: UUID
    event_id: UUID
    category_id: UUID
    ticket_code: str
    status: TicketStatus
    checked_in_at: datetime | None = None
    _domain_events: List[DomainEvent] = field(default_factory=list, repr=False)

    # ── Factory ───────────────────────────────────────────────────────────────

    @classmethod
    def issue(
        cls,
        booking_id: UUID,
        customer_id: UUID,
        event_id: UUID,
        category_id: UUID,
    ) -> "Ticket":
        return cls(
            id=uuid4(),
            booking_id=booking_id,
            customer_id=customer_id,
            event_id=event_id,
            category_id=category_id,
            ticket_code=cls._generate_code(),
            status=TicketStatus.ACTIVE,
        )

    # ── Commands ──────────────────────────────────────────────────────────────

    def check_in(self, gate_event_id: UUID) -> None:
        if gate_event_id != self.event_id:
            raise ValueError("Ticket does not belong to this event")
        if self.status == TicketStatus.CHECKED_IN:
            raise ValueError("Ticket has already been checked in")
        if self.status != TicketStatus.ACTIVE:
            raise ValueError("Only Active tickets can be checked in")
        self.status = TicketStatus.CHECKED_IN
        self.checked_in_at = datetime.utcnow()
        self._domain_events.append(
            TicketCheckedIn(ticket_id=self.id, event_id=self.event_id)
        )

    def cancel(self) -> None:
        if self.status == TicketStatus.CHECKED_IN:
            raise ValueError("Checked-in ticket cannot be cancelled")
        self.status = TicketStatus.CANCELLED

    # ── Queries ───────────────────────────────────────────────────────────────

    def is_checked_in(self) -> bool:
        return self.status == TicketStatus.CHECKED_IN

    def pull_domain_events(self) -> List[DomainEvent]:
        events = list(self._domain_events)
        self._domain_events.clear()
        return events

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _generate_code(length: int = 12) -> str:
        alphabet = string.ascii_uppercase + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(length))