from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import List
from uuid import UUID, uuid4

from src.domain.events.domain_events import (
    BookingExpired,
    BookingPaid,
    DomainEvent,
    TicketReserved,
)
from src.domain.value_objects.money import Money


# ── Enum ──────────────────────────────────────────────────────────────────────

class BookingStatus(Enum):
    PENDING_PAYMENT = "PendingPayment"
    PAID = "Paid"
    EXPIRED = "Expired"
    REFUNDED = "Refunded"


# ── Aggregate Root: Booking ───────────────────────────────────────────────────

@dataclass
class Booking:
    id: UUID
    customer_id: UUID
    event_id: UUID
    category_id: UUID
    quantity: int
    unit_price: Money
    service_fee: Money
    payment_deadline: datetime
    status: BookingStatus
    _domain_events: List[DomainEvent] = field(default_factory=list, repr=False)

    # ── Factory ───────────────────────────────────────────────────────────────

    @classmethod
    def create(
        cls,
        customer_id: UUID,
        event_id: UUID,
        category_id: UUID,
        quantity: int,
        unit_price: Money,
        service_fee: Money | None = None,
        payment_deadline_minutes: int = 15,
    ) -> "Booking":
        if quantity <= 0:
            raise ValueError("Ticket quantity must be greater than zero")

        if service_fee is None:
            service_fee = Money.of(0, unit_price.currency)

        booking = cls(
            id=uuid4(),
            customer_id=customer_id,
            event_id=event_id,
            category_id=category_id,
            quantity=quantity,
            unit_price=unit_price,
            service_fee=service_fee,
            payment_deadline=datetime.utcnow() + timedelta(minutes=payment_deadline_minutes),
            status=BookingStatus.PENDING_PAYMENT,
        )
        booking._domain_events.append(
            TicketReserved(
                booking_id=booking.id,
                customer_id=customer_id,
                event_id=event_id,
            )
        )
        return booking

    # ── Commands ──────────────────────────────────────────────────────────────

    def pay(self, amount_paid: Money) -> None:
        if self.status != BookingStatus.PENDING_PAYMENT:
            raise ValueError("Booking can only be paid when status is PendingPayment")
        if datetime.utcnow() > self.payment_deadline:
            raise ValueError("Payment deadline has passed")
        if amount_paid != self.total_price:
            raise ValueError(
                f"Payment amount {amount_paid} does not match total price {self.total_price}"
            )
        self.status = BookingStatus.PAID
        self._domain_events.append(
            BookingPaid(booking_id=self.id, customer_id=self.customer_id)
        )

    def expire(self) -> None:
        if self.status == BookingStatus.PAID:
            raise ValueError("Paid booking cannot be expired")
        if self.status != BookingStatus.PENDING_PAYMENT:
            raise ValueError("Only PendingPayment bookings can be expired")
        self.status = BookingStatus.EXPIRED
        self._domain_events.append(BookingExpired(booking_id=self.id))

    def mark_as_refunded(self) -> None:
        if self.status != BookingStatus.PAID:
            raise ValueError("Only Paid bookings can be marked as refunded")
        self.status = BookingStatus.REFUNDED

    # ── Queries ───────────────────────────────────────────────────────────────

    @property
    def total_price(self) -> Money:
        subtotal = self.unit_price.multiply(self.quantity)
        return subtotal.add(self.service_fee)

    def is_expired(self) -> bool:
        return datetime.utcnow() > self.payment_deadline

    def pull_domain_events(self) -> List[DomainEvent]:
        events = list(self._domain_events)
        self._domain_events.clear()
        return events