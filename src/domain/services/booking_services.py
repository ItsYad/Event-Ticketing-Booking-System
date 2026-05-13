from __future__ import annotations

from datetime import datetime
from uuid import UUID

from src.domain.aggregates.booking import Booking, BookingStatus
from src.domain.aggregates.event import Event, EventStatus, TicketCategory
from src.domain.aggregates.ticket import Ticket, TicketStatus
from src.domain.value_objects.money import Money


class BookingDomainService:
    """
    Domain Service: menangani logika pembuatan booking yang melibatkan
    lebih dari satu aggregate (Event + Booking).
    """

    @staticmethod
    def create_booking(
        customer_id: UUID,
        event: Event,
        category_id: UUID,
        quantity: int,
        service_fee: Money | None = None,
        payment_deadline_minutes: int = 15,
    ) -> Booking:
        """
        Memvalidasi semua aturan bisnis sebelum membuat booking baru.
        Mengurangi quota pada TicketCategory di dalam Event aggregate.
        """
        # Event harus berstatus Published
        if event.status != EventStatus.PUBLISHED:
            raise ValueError("Booking can only be created for a Published event")

        # Cari ticket category yang diminta
        category: TicketCategory = event.get_category(category_id)

        # Kategori harus aktif
        from src.domain.aggregates.event import TicketCategoryStatus
        if category.status != TicketCategoryStatus.ACTIVE:
            raise ValueError("Booking can only be created for an active ticket category")

        # Harus dalam periode penjualan
        now = datetime.utcnow()
        if now < category.sales_start:
            raise ValueError("Ticket sales period has not started yet")
        if now > category.sales_end:
            raise ValueError("Ticket sales period has ended")

        # Reservasi quota (validasi quantity & sisa quota ada di dalam category.reserve)
        category.reserve(quantity)

        # Buat booking
        booking = Booking.create(
            customer_id=customer_id,
            event_id=event.id,
            category_id=category_id,
            quantity=quantity,
            unit_price=category.price,
            service_fee=service_fee,
            payment_deadline_minutes=payment_deadline_minutes,
        )
        return booking


class RefundDomainService:
    """
    Domain Service: menangani validasi logika refund yang
    melibatkan Booking dan Ticket aggregate.
    """

    @staticmethod
    def validate_refund_request(
        booking: Booking,
        tickets: list[Ticket],
        refund_deadline: datetime | None = None,
        event_cancelled: bool = False,
    ) -> None:
        """
        Memvalidasi apakah refund boleh diminta.
        Raise ValueError jika tidak memenuhi aturan bisnis.
        """
        # Booking harus berstatus Paid
        if booking.status != BookingStatus.PAID:
            raise ValueError("Refund can only be requested for a Paid booking")

        # Tidak boleh ada tiket yang sudah check-in
        checked_in = [t for t in tickets if t.status == TicketStatus.CHECKED_IN]
        if checked_in:
            raise ValueError(
                "Refund cannot be requested because one or more tickets have already been checked in"
            )

        # Jika event dibatalkan, refund otomatis diizinkan (skip deadline check)
        if event_cancelled:
            return

        # Cek deadline refund jika diberikan
        if refund_deadline is not None and datetime.utcnow() > refund_deadline:
            raise ValueError("Refund deadline has passed")