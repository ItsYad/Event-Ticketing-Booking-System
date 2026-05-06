"""
In-Memory Repository Implementations
Untuk keperluan development dan testing di Week 8.
Nanti di Week 12 akan diganti dengan implementasi PostgreSQL.

Ini adalah implementasi sederhana menggunakan Python dictionary.
"""
from typing import Dict, List, Optional
from datetime import datetime, timezone
from uuid import UUID

from src.domain.aggregates.event import Event
from src.domain.aggregates.booking import Booking, BookingStatus
from src.domain.aggregates.refund import Refund
from src.domain.repositories.interfaces import (
    IEventRepository, IBookingRepository, IRefundRepository
)


class InMemoryEventRepository(IEventRepository):
    """
    Repository Event menggunakan memori (dictionary).
    Data hilang saat aplikasi restart - hanya untuk development!
    """

    def __init__(self):
        self._store: Dict[UUID, Event] = {}

    async def save(self, event: Event) -> None:
        self._store[event.event_id] = event

    async def get_by_id(self, event_id: UUID) -> Optional[Event]:
        return self._store.get(event_id)

    async def get_published_events(self) -> List[Event]:
        from src.domain.aggregates.event import EventStatus
        return [
            e for e in self._store.values()
            if e.status == EventStatus.PUBLISHED
        ]

    async def delete(self, event_id: UUID) -> None:
        self._store.pop(event_id, None)

    def get_all(self) -> List[Event]:
        """Helper untuk debugging - ambil semua event"""
        return list(self._store.values())


class InMemoryBookingRepository(IBookingRepository):
    """Repository Booking menggunakan memori"""

    def __init__(self):
        self._store: Dict[UUID, Booking] = {}

    async def save(self, booking: Booking) -> None:
        self._store[booking.booking_id] = booking

    async def get_by_id(self, booking_id: UUID) -> Optional[Booking]:
        return self._store.get(booking_id)

    async def get_by_customer_and_event(
        self, customer_id: UUID, event_id: UUID
    ) -> Optional[Booking]:
        """Cari booking aktif (PendingPayment atau Paid) milik customer untuk event"""
        for booking in self._store.values():
            if (
                booking.customer_id == customer_id
                and booking.event_id == event_id
                and booking.status in [BookingStatus.PENDING_PAYMENT, BookingStatus.PAID]
            ):
                return booking
        return None

    async def get_expired_pending_bookings(self) -> List[Booking]:
        """Ambil booking yang sudah melewati payment deadline"""
        now = datetime.now(timezone.utc)
        return [
            b for b in self._store.values()
            if b.status == BookingStatus.PENDING_PAYMENT and b.payment_deadline < now
        ]

    def get_all(self) -> List[Booking]:
        return list(self._store.values())


class InMemoryRefundRepository(IRefundRepository):
    """Repository Refund menggunakan memori"""

    def __init__(self):
        self._store: Dict[UUID, Refund] = {}

    async def save(self, refund: Refund) -> None:
        self._store[refund.refund_id] = refund

    async def get_by_id(self, refund_id: UUID) -> Optional[Refund]:
        return self._store.get(refund_id)

    async def get_by_booking_id(self, booking_id: UUID) -> Optional[Refund]:
        for refund in self._store.values():
            if refund.booking_id == booking_id:
                return refund
        return None

    def get_all(self) -> List[Refund]:
        return list(self._store.values())


class InMemoryTicketRepository:
    """Repository Ticket menggunakan memori"""

    def __init__(self):
        self._store: Dict[UUID, "Ticket"] = {}

    async def save(self, ticket) -> None:
        self._store[ticket.ticket_id] = ticket

    async def get_by_id(self, ticket_id: UUID):
        return self._store.get(ticket_id)

    async def get_by_code(self, ticket_code: str):
        for ticket in self._store.values():
            if ticket.ticket_code == ticket_code:
                return ticket
        return None

    async def get_by_booking_id(self, booking_id: UUID) -> list:
        return [t for t in self._store.values() if t.booking_id == booking_id]

    def get_all(self) -> list:
        return list(self._store.values())
