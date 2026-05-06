"""
Aggregate: Event
Aggregate Root yang mengelola data Event dan Ticket Categories.

Aggregate = kumpulan Entity dan Value Object yang diperlakukan sebagai satu unit.
Aggregate Root = pintu masuk satu-satunya untuk memodifikasi data dalam aggregate.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
from uuid import UUID, uuid4

from ..value_objects.money import Money
from ..events.domain_events import (
    DomainEvent, EventCreated, EventPublished,
    EventCancelled, TicketCategoryCreated, TicketCategoryDisabled
)


class EventStatus(str, Enum):
    """Status lifecycle sebuah Event"""
    DRAFT = "Draft"
    PUBLISHED = "Published"
    CANCELLED = "Cancelled"
    COMPLETED = "Completed"


class TicketCategoryStatus(str, Enum):
    """Status sebuah Ticket Category"""
    ACTIVE = "Active"
    INACTIVE = "Inactive"


@dataclass
class TicketCategory:
    """
    Entity: TicketCategory
    Merepresentasikan tipe tiket dalam sebuah event (Regular, VIP, Early Bird).
    Entity = memiliki identity unik (category_id)
    """
    category_id: UUID
    event_id: UUID
    name: str
    price: Money
    quota: int
    sales_start_date: datetime
    sales_end_date: datetime
    status: TicketCategoryStatus = TicketCategoryStatus.ACTIVE
    booked_quota: int = 0  # Quota yang sudah dipesan

    @property
    def remaining_quota(self) -> int:
        """Sisa quota yang bisa dipesan"""
        return self.quota - self.booked_quota

    @property
    def is_active(self) -> bool:
        return self.status == TicketCategoryStatus.ACTIVE

    def is_on_sale(self, at: datetime) -> bool:
        """Apakah tiket sedang dalam masa penjualan?"""
        return self.sales_start_date <= at <= self.sales_end_date

    def disable(self) -> None:
        """Nonaktifkan ticket category ini"""
        self.status = TicketCategoryStatus.INACTIVE

    def reserve(self, quantity: int) -> None:
        """Reservasi sejumlah tiket (kurangi quota)"""
        if quantity <= 0:
            raise ValueError("Quantity harus lebih dari 0")
        if quantity > self.remaining_quota:
            raise ValueError(f"Quota tidak cukup. Tersisa: {self.remaining_quota}")
        self.booked_quota += quantity

    def release(self, quantity: int) -> None:
        """Lepas reservasi (kembalikan quota)"""
        self.booked_quota = max(0, self.booked_quota - quantity)


@dataclass
class Event:
    """
    Aggregate Root: Event
    
    Mengelola semua operasi terkait Event dan Ticket Categories.
    Semua perubahan state harus melalui method di class ini.
    """
    event_id: UUID
    organizer_id: UUID
    name: str
    description: str
    location: str
    start_date: datetime
    end_date: datetime
    max_capacity: int
    status: EventStatus = EventStatus.DRAFT
    ticket_categories: List[TicketCategory] = field(default_factory=list)
    _domain_events: List[DomainEvent] = field(default_factory=list, repr=False)

    def __post_init__(self):
        """Validasi business rules saat inisialisasi"""
        pass  # Validasi dilakukan di factory method

    # ============================================================
    # FACTORY METHOD (cara membuat Event yang valid)
    # ============================================================

    @classmethod
    def create(
        cls,
        organizer_id: UUID,
        name: str,
        description: str,
        location: str,
        start_date: datetime,
        end_date: datetime,
        max_capacity: int,
    ) -> "Event":
        """
        Factory method untuk membuat Event baru.
        Memastikan semua business rules terpenuhi saat pembuatan.
        """
        # Business Rule: end_date tidak boleh lebih awal dari start_date
        if end_date < start_date:
            raise ValueError("Tanggal selesai tidak boleh lebih awal dari tanggal mulai")

        # Business Rule: max_capacity harus lebih dari 0
        if max_capacity <= 0:
            raise ValueError("Kapasitas maksimal harus lebih dari 0")

        event = cls(
            event_id=uuid4(),
            organizer_id=organizer_id,
            name=name,
            description=description,
            location=location,
            start_date=start_date,
            end_date=end_date,
            max_capacity=max_capacity,
            status=EventStatus.DRAFT,
        )

        # Raise Domain Event
        event._domain_events.append(
            EventCreated(
                event_id_ref=event.event_id,
                event_name=name,
                organizer_id=organizer_id,
            )
        )
        return event

    # ============================================================
    # COMMANDS (operasi yang mengubah state)
    # ============================================================

    def publish(self) -> None:
        """
        Publish event agar bisa dilihat dan dibeli customer.
        
        Business Rules:
        - Harus ada minimal 1 ticket category yang aktif
        - Total quota tidak boleh melebihi max_capacity
        - Status harus Draft (tidak bisa publish ulang yang Cancelled)
        """
        if self.status == EventStatus.CANCELLED:
            raise ValueError("Event yang sudah dibatalkan tidak bisa dipublish")

        active_categories = [tc for tc in self.ticket_categories if tc.is_active]
        if not active_categories:
            raise ValueError("Event harus memiliki minimal 1 ticket category aktif sebelum dipublish")

        total_quota = sum(tc.quota for tc in active_categories)
        if total_quota > self.max_capacity:
            raise ValueError(
                f"Total quota tiket ({total_quota}) melebihi kapasitas maksimal ({self.max_capacity})"
            )

        self.status = EventStatus.PUBLISHED
        self._domain_events.append(
            EventPublished(event_id_ref=self.event_id, event_name=self.name)
        )

    def cancel(self, reason: str = "") -> None:
        """
        Batalkan event.
        
        Business Rules:
        - Event yang Completed tidak bisa dibatalkan
        """
        if self.status == EventStatus.COMPLETED:
            raise ValueError("Event yang sudah selesai tidak bisa dibatalkan")

        self.status = EventStatus.CANCELLED
        self._domain_events.append(
            EventCancelled(event_id_ref=self.event_id, reason=reason)
        )

    def add_ticket_category(
        self,
        name: str,
        price: Money,
        quota: int,
        sales_start_date: datetime,
        sales_end_date: datetime,
    ) -> TicketCategory:
        """
        Tambah Ticket Category ke Event ini.
        
        Business Rules:
        - Harga tidak boleh negatif (sudah divalidasi di Money)
        - Quota harus lebih dari 0
        - Sales period harus sebelum atau saat event mulai
        - Total quota tidak boleh melebihi max_capacity
        """
        if quota <= 0:
            raise ValueError("Quota tiket harus lebih dari 0")

        if sales_end_date > self.start_date:
            raise ValueError("Periode penjualan harus berakhir sebelum atau saat event dimulai")

        # Cek total quota tidak melebihi kapasitas
        current_total_quota = sum(tc.quota for tc in self.ticket_categories if tc.is_active)
        if current_total_quota + quota > self.max_capacity:
            raise ValueError(
                f"Penambahan quota ({quota}) akan melebihi kapasitas maksimal ({self.max_capacity}). "
                f"Quota saat ini: {current_total_quota}"
            )

        category = TicketCategory(
            category_id=uuid4(),
            event_id=self.event_id,
            name=name,
            price=price,
            quota=quota,
            sales_start_date=sales_start_date,
            sales_end_date=sales_end_date,
        )
        self.ticket_categories.append(category)

        self._domain_events.append(
            TicketCategoryCreated(
                event_id_ref=self.event_id,
                category_id=category.category_id,
                category_name=name,
            )
        )
        return category

    def disable_ticket_category(self, category_id: UUID) -> None:
        """
        Nonaktifkan sebuah Ticket Category.
        
        Business Rules:
        - Event tidak boleh sudah Completed
        """
        if self.status == EventStatus.COMPLETED:
            raise ValueError("Tidak bisa menonaktifkan ticket category pada event yang sudah selesai")

        category = self._find_category(category_id)
        category.disable()

        self._domain_events.append(
            TicketCategoryDisabled(category_id=category_id)
        )

    # ============================================================
    # QUERIES (operasi baca saja, tidak mengubah state)
    # ============================================================

    def get_active_categories(self) -> List[TicketCategory]:
        """Ambil semua ticket category yang aktif"""
        return [tc for tc in self.ticket_categories if tc.is_active]

    def get_lowest_price(self) -> Optional[Money]:
        """Ambil harga tiket terendah dari semua kategori aktif"""
        active = self.get_active_categories()
        if not active:
            return None
        return min(active, key=lambda tc: tc.price.amount).price

    def is_published(self) -> bool:
        return self.status == EventStatus.PUBLISHED

    # ============================================================
    # DOMAIN EVENT MANAGEMENT
    # ============================================================

    def pull_domain_events(self) -> List[DomainEvent]:
        """
        Ambil semua domain events yang belum diproses, lalu kosongkan list-nya.
        Pattern ini disebut 'collect and clear'.
        """
        events = list(self._domain_events)
        self._domain_events.clear()
        return events

    # ============================================================
    # PRIVATE HELPERS
    # ============================================================

    def _find_category(self, category_id: UUID) -> TicketCategory:
        """Cari ticket category by ID, raise error jika tidak ditemukan"""
        for tc in self.ticket_categories:
            if tc.category_id == category_id:
                return tc
        raise ValueError(f"Ticket category dengan ID {category_id} tidak ditemukan")
