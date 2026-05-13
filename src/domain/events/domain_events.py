from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class DomainEvent:
    occurred_at: datetime = field(default_factory=datetime.utcnow)


# ── Event Management ──────────────────────────────────────────────────────────

@dataclass(frozen=True)
class EventCreated(DomainEvent):
    event_id: UUID = field(default=None)
    name: str = field(default="")


@dataclass(frozen=True)
class EventPublished(DomainEvent):
    event_id: UUID = field(default=None)


@dataclass(frozen=True)
class EventCancelled(DomainEvent):
    event_id: UUID = field(default=None)


# ── Ticket Category ───────────────────────────────────────────────────────────

@dataclass(frozen=True)
class TicketCategoryCreated(DomainEvent):
    event_id: UUID = field(default=None)
    category_id: UUID = field(default=None)
    name: str = field(default="")


@dataclass(frozen=True)
class TicketCategoryDisabled(DomainEvent):
    event_id: UUID = field(default=None)
    category_id: UUID = field(default=None)


# ── Booking ───────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class TicketReserved(DomainEvent):
    booking_id: UUID = field(default=None)
    customer_id: UUID = field(default=None)
    event_id: UUID = field(default=None)


@dataclass(frozen=True)
class BookingPaid(DomainEvent):
    booking_id: UUID = field(default=None)
    customer_id: UUID = field(default=None)


@dataclass(frozen=True)
class BookingExpired(DomainEvent):
    booking_id: UUID = field(default=None)


# ── Ticket ────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class TicketCheckedIn(DomainEvent):
    ticket_id: UUID = field(default=None)
    event_id: UUID = field(default=None)


# ── Refund ────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class RefundRequested(DomainEvent):
    refund_id: UUID = field(default=None)
    booking_id: UUID = field(default=None)
    customer_id: UUID = field(default=None)


@dataclass(frozen=True)
class RefundApproved(DomainEvent):
    refund_id: UUID = field(default=None)
    booking_id: UUID = field(default=None)


@dataclass(frozen=True)
class RefundRejected(DomainEvent):
    refund_id: UUID = field(default=None)
    booking_id: UUID = field(default=None)
    reason: str = field(default="")


@dataclass(frozen=True)
class RefundPaidOut(DomainEvent):
    refund_id: UUID = field(default=None)
    payment_reference: str = field(default="")