"""
Aggregate: Booking
Mengelola proses pemesanan tiket dari reservasi hingga pembayaran.
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import List, Optional
from uuid import UUID, uuid4
import secrets
import string

from ..value_objects.money import Money
from ..events.domain_events import (
    DomainEvent, TicketReserved, BookingPaid, BookingExpired
)


class BookingStatus(str, Enum):
    """Status lifecycle sebuah Booking"""
    PENDING_PAYMENT = "PendingPayment"
    PAID = "Paid"
    EXPIRED = "Expired"
    REFUNDED = "Refunded"


class TicketStatus(str, Enum):
    """Status sebuah Ticket"""
    ACTIVE = "Active"
    CHECKED_IN = "CheckedIn"
    CANCELLED = "Cancelled"


@dataclass
class Ticket:
    """
    Entity: Ticket
    Bukti pembelian yang dihasilkan setelah booking dibayar.
    """
    ticket_id: UUID
    booking_id: UUID
    ticket_code: str  # Unique code untuk check-in
    status: TicketStatus = TicketStatus.ACTIVE

    def check_in(self) -> None:
        """Check in tiket ini"""
        if self.status != TicketStatus.ACTIVE:
            raise ValueError(f"Tiket tidak bisa di-check in. Status saat ini: {self.status.value}")
        self.status = TicketStatus.CHECKED_IN

    def cancel(self) -> None:
        """Batalkan tiket ini"""
        self.status = TicketStatus.CANCELLED

    @property
    def is_checked_in(self) -> bool:
        return self.status == TicketStatus.CHECKED_IN


@dataclass
class Booking:
    """
    Aggregate Root: Booking
    Mengelola proses pemesanan tiket.
    """
    booking_id: UUID
    customer_id: UUID
    event_id: UUID
    category_id: UUID
    ticket_quantity: int
    unit_price: Money
    payment_deadline: datetime
    status: BookingStatus = BookingStatus.PENDING_PAYMENT
    tickets: List[Ticket] = field(default_factory=list)
    _domain_events: List[DomainEvent] = field(default_factory=list, repr=False)

    # ── FACTORY METHOD ───────────────────────────────────────

    @classmethod
    def create(
        cls,
        customer_id: UUID,
        event_id: UUID,
        category_id: UUID,
        ticket_quantity: int,
        unit_price: Money,
        payment_deadline_minutes: int = 15,
    ) -> "Booking":
        """
        Factory method untuk membuat Booking baru.

        Business Rules:
        - Quantity harus lebih dari 0
        - Payment deadline diset otomatis 15 menit dari sekarang
        """
        if ticket_quantity <= 0:
            raise ValueError("Jumlah tiket harus lebih dari 0")

        now = datetime.now(timezone.utc)
        booking = cls(
            booking_id=uuid4(),
            customer_id=customer_id,
            event_id=event_id,
            category_id=category_id,
            ticket_quantity=ticket_quantity,
            unit_price=unit_price,
            payment_deadline=now + timedelta(minutes=payment_deadline_minutes),
            status=BookingStatus.PENDING_PAYMENT,
        )

        booking._domain_events.append(
            TicketReserved(
                booking_id=booking.booking_id,
                customer_id=customer_id,
                event_id_ref=event_id,
            )
        )
        return booking

    # ── COMMANDS ─────────────────────────────────────────────

    def pay(self, payment_amount: Money, paid_at: Optional[datetime] = None) -> None:
        """
        Bayar booking ini.

        Business Rules:
        - Status harus PendingPayment
        - Tidak boleh lewat payment deadline
        - Jumlah pembayaran harus sama dengan total price
        """
        if self.status != BookingStatus.PENDING_PAYMENT:
            raise ValueError(f"Booking tidak bisa dibayar. Status: {self.status.value}")

        check_time = paid_at or datetime.now(timezone.utc)

        # Normalize timezone untuk perbandingan yang aman
        deadline = self.payment_deadline
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)
        if check_time.tzinfo is None:
            check_time = check_time.replace(tzinfo=timezone.utc)

        if check_time > deadline:
            raise ValueError("Batas waktu pembayaran sudah lewat")

        if payment_amount != self.total_price:
            raise ValueError(
                f"Jumlah pembayaran ({payment_amount}) tidak sesuai "
                f"dengan total harga ({self.total_price})"
            )

        self.status = BookingStatus.PAID

        # Generate tiket untuk setiap quantity
        for _ in range(self.ticket_quantity):
            ticket = Ticket(
                ticket_id=uuid4(),
                booking_id=self.booking_id,
                ticket_code=self._generate_ticket_code(),
            )
            self.tickets.append(ticket)

        self._domain_events.append(
            BookingPaid(
                booking_id=self.booking_id,
                customer_id=self.customer_id,
            )
        )

    def expire(self) -> None:
        """
        Tandai booking sebagai expired.

        Business Rules:
        - Status harus PendingPayment (yang sudah Paid tidak bisa di-expire)
        """
        if self.status == BookingStatus.PAID:
            raise ValueError("Booking yang sudah dibayar tidak bisa di-expire")

        if self.status != BookingStatus.PENDING_PAYMENT:
            return  # Sudah expired atau refunded, abaikan

        self.status = BookingStatus.EXPIRED
        self._domain_events.append(
            BookingExpired(
                booking_id=self.booking_id,
                customer_id=self.customer_id,
            )
        )

    # ── QUERIES ──────────────────────────────────────────────

    @property
    def total_price(self) -> Money:
        """Hitung total harga booking"""
        return self.unit_price.multiply(self.ticket_quantity)

    def is_expired(self) -> bool:
        """Cek apakah booking sudah melewati payment deadline"""
        now = datetime.now(timezone.utc)
        deadline = self.payment_deadline
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)
        return now > deadline

    def has_checked_in_tickets(self) -> bool:
        """Cek apakah ada tiket yang sudah check-in"""
        return any(t.is_checked_in for t in self.tickets)

    # ── DOMAIN EVENT MANAGEMENT ──────────────────────────────

    def pull_domain_events(self) -> List[DomainEvent]:
        events = list(self._domain_events)
        self._domain_events.clear()
        return events

    # ── PRIVATE HELPERS ──────────────────────────────────────

    @staticmethod
    def _generate_ticket_code() -> str:
        """Generate unique ticket code (contoh: TKT-AB12CD34)"""
        chars = string.ascii_uppercase + string.digits
        random_part = "".join(secrets.choice(chars) for _ in range(8))
        return f"TKT-{random_part}"
