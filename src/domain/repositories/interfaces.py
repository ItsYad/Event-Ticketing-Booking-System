"""
Repository Interfaces (Abstract)
Mendefinisikan kontrak untuk menyimpan dan mengambil Aggregate dari storage.

Repository = abstraksi untuk menyembunyikan detail penyimpanan data.
Interface ini ada di Domain Layer, implementasinya ada di Infrastructure Layer.
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from ..aggregates.event import Event
from ..aggregates.ticket import Ticket
from ..aggregates.booking import Booking
from ..aggregates.refund import Refund


class IEventRepository(ABC):
    """Interface untuk menyimpan dan mengambil Event aggregate"""

    @abstractmethod
    async def save(self, event: Event) -> None:
        """Simpan event (create atau update)"""
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, event_id: UUID) -> Optional[Event]:
        """Ambil event berdasarkan ID"""
        raise NotImplementedError

    @abstractmethod
    async def get_published_events(self) -> List[Event]:
        """Ambil semua event yang sudah dipublish"""
        raise NotImplementedError

    @abstractmethod
    async def delete(self, event_id: UUID) -> None:
        """Hapus event berdasarkan ID"""
        raise NotImplementedError


class IBookingRepository(ABC):
    """Interface untuk menyimpan dan mengambil Booking aggregate"""

    @abstractmethod
    async def save(self, booking: Booking) -> None:
        """Simpan booking (create atau update)"""
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, booking_id: UUID) -> Optional[Booking]:
        """Ambil booking berdasarkan ID"""
        raise NotImplementedError

    @abstractmethod
    async def get_by_customer_and_event(
        self, customer_id: UUID, event_id: UUID
    ) -> Optional[Booking]:
        """Ambil booking aktif milik customer untuk event tertentu"""
        raise NotImplementedError

    @abstractmethod
    async def get_expired_pending_bookings(self) -> List[Booking]:
        """Ambil semua booking PendingPayment yang sudah melewati deadline"""
        raise NotImplementedError


class IRefundRepository(ABC):
    """Interface untuk menyimpan dan mengambil Refund aggregate"""

    @abstractmethod
    async def save(self, refund: Refund) -> None:
        """Simpan refund (create atau update)"""
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, refund_id: UUID) -> Optional[Refund]:
        """Ambil refund berdasarkan ID"""
        raise NotImplementedError

    @abstractmethod
    async def get_by_booking_id(self, booking_id: UUID) -> Optional[Refund]:
        """Ambil refund berdasarkan booking ID"""
        raise NotImplementedError


class ITicketRepository(ABC):
    """Interface untuk menyimpan dan mengambil Ticket aggregate"""

    @abstractmethod
    async def save(self, ticket: "Ticket") -> None:
        """Simpan ticket"""
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, ticket_id: UUID) -> Optional["Ticket"]:
        """Ambil ticket berdasarkan ID"""
        raise NotImplementedError

    @abstractmethod
    async def get_by_code(self, ticket_code: str) -> Optional["Ticket"]:
        """Ambil ticket berdasarkan ticket code (untuk check-in)"""
        raise NotImplementedError

    @abstractmethod
    async def get_by_booking_id(self, booking_id: UUID) -> list:
        """Ambil semua ticket milik sebuah booking"""
        raise NotImplementedError
