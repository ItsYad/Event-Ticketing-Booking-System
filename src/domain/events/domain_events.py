"""
Domain Events
Merepresentasikan kejadian penting yang terjadi di domain.
Domain Event = sesuatu yang SUDAH terjadi (past tense)
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


def _now():
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class DomainEvent:
    """Base class untuk semua Domain Event"""
    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=_now)


# ── EVENT MANAGEMENT ─────────────────────────────────────────

@dataclass(frozen=True)
class EventCreated(DomainEvent):
    """Raised ketika Event baru berhasil dibuat"""
    event_id_ref: UUID = field(default=None)
    event_name: str = field(default="")
    organizer_id: UUID = field(default=None)


@dataclass(frozen=True)
class EventPublished(DomainEvent):
    """Raised ketika Event dipublish dan siap dijual"""
    event_id_ref: UUID = field(default=None)
    event_name: str = field(default="")


@dataclass(frozen=True)
class EventCancelled(DomainEvent):
    """Raised ketika Event dibatalkan"""
    event_id_ref: UUID = field(default=None)
    reason: str = field(default="")


# ── TICKET CATEGORY ──────────────────────────────────────────

@dataclass(frozen=True)
class TicketCategoryCreated(DomainEvent):
    """Raised ketika Ticket Category baru dibuat"""
    event_id_ref: UUID = field(default=None)
    category_id: UUID = field(default=None)
    category_name: str = field(default="")


@dataclass(frozen=True)
class TicketCategoryDisabled(DomainEvent):
    """Raised ketika Ticket Category dinonaktifkan"""
    category_id: UUID = field(default=None)


# ── BOOKING ──────────────────────────────────────────────────

@dataclass(frozen=True)
class TicketReserved(DomainEvent):
    """Raised ketika Booking berhasil dibuat (tiket direservasi)"""
    booking_id: UUID = field(default=None)
    customer_id: UUID = field(default=None)
    event_id_ref: UUID = field(default=None)


@dataclass(frozen=True)
class BookingPaid(DomainEvent):
    """Raised ketika Booking berhasil dibayar"""
    booking_id: UUID = field(default=None)
    customer_id: UUID = field(default=None)


@dataclass(frozen=True)
class BookingExpired(DomainEvent):
    """Raised ketika Booking expired karena tidak dibayar tepat waktu"""
    booking_id: UUID = field(default=None)
    customer_id: UUID = field(default=None)


# ── TICKET CHECK-IN ──────────────────────────────────────────

@dataclass(frozen=True)
class TicketCheckedIn(DomainEvent):
    """Raised ketika Tiket berhasil di-check in"""
    ticket_id: UUID = field(default=None)
    ticket_code: str = field(default="")


# ── REFUND ───────────────────────────────────────────────────

@dataclass(frozen=True)
class RefundRequested(DomainEvent):
    """Raised ketika Customer meminta refund"""
    refund_id: UUID = field(default=None)
    booking_id: UUID = field(default=None)
    customer_id: UUID = field(default=None)


@dataclass(frozen=True)
class RefundApproved(DomainEvent):
    """Raised ketika Refund disetujui oleh Event Organizer"""
    refund_id: UUID = field(default=None)


@dataclass(frozen=True)
class RefundRejected(DomainEvent):
    """Raised ketika Refund ditolak oleh Event Organizer"""
    refund_id: UUID = field(default=None)
    reason: str = field(default="")


@dataclass(frozen=True)
class RefundPaidOut(DomainEvent):
    """Raised ketika Refund sudah dibayarkan ke customer"""
    refund_id: UUID = field(default=None)
    payment_reference: str = field(default="")
