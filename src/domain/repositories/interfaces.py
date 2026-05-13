from __future__ import annotations
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from src.domain.aggregates.booking import Booking
from src.domain.aggregates.event import Event
from src.domain.aggregates.refund import Refund
from src.domain.aggregates.ticket import Ticket


class IEventRepository(ABC):
    @abstractmethod
    def save(self, event: Event) -> None: ...

    @abstractmethod
    def get_by_id(self, event_id: UUID) -> Optional[Event]: ...

    @abstractmethod
    def get_published_events(self) -> List[Event]: ...

    @abstractmethod
    def delete(self, event_id: UUID) -> None: ...


class IBookingRepository(ABC):
    @abstractmethod
    def save(self, booking: Booking) -> None: ...

    @abstractmethod
    def get_by_id(self, booking_id: UUID) -> Optional[Booking]: ...

    @abstractmethod
    def get_by_customer_and_event(
        self, customer_id: UUID, event_id: UUID
    ) -> Optional[Booking]: ...

    @abstractmethod
    def get_expired_pending_bookings(self, as_of: datetime) -> List[Booking]: ...


class ITicketRepository(ABC):
    @abstractmethod
    def save(self, ticket: Ticket) -> None: ...

    @abstractmethod
    def get_by_id(self, ticket_id: UUID) -> Optional[Ticket]: ...

    @abstractmethod
    def get_by_code(self, ticket_code: str) -> Optional[Ticket]: ...

    @abstractmethod
    def get_by_booking_id(self, booking_id: UUID) -> List[Ticket]: ...


class IRefundRepository(ABC):
    @abstractmethod
    def save(self, refund: Refund) -> None: ...

    @abstractmethod
    def get_by_id(self, refund_id: UUID) -> Optional[Refund]: ...

    @abstractmethod
    def get_by_booking_id(self, booking_id: UUID) -> Optional[Refund]: ...