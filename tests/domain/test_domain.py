"""
Unit Tests – Domain Layer
Event Ticketing & Booking System
Week 9: Domain Layer & Unit Tests

Covers semua minimum test cases yang diwajibkan dalam case study,
plus test tambahan untuk branch coverage yang lebih lengkap.
"""

from __future__ import annotations

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from src.domain.aggregates.booking import Booking, BookingStatus
from src.domain.aggregates.event import Event, EventStatus, TicketCategory, TicketCategoryStatus
from src.domain.aggregates.refund import Refund, RefundStatus
from src.domain.aggregates.ticket import Ticket, TicketStatus
from src.domain.events.domain_events import (
    BookingExpired,
    BookingPaid,
    EventCancelled,
    EventCreated,
    EventPublished,
    RefundApproved,
    RefundPaidOut,
    RefundRejected,
    RefundRequested,
    TicketCategoryCreated,
    TicketCategoryDisabled,
    TicketCheckedIn,
    TicketReserved,
)
from src.domain.services.booking_service import BookingDomainService, RefundDomainService
from src.domain.value_objects.money import Money


# =============================================================================
# Helpers / Fixtures
# =============================================================================

def make_event(
    max_capacity: int = 100,
    start_offset_days: int = 10,
    end_offset_days: int = 11,
) -> Event:
    now = datetime.utcnow()
    return Event.create(
        organizer_id=uuid4(),
        name="Tech Conference 2025",
        description="Annual tech conference",
        start_date=now + timedelta(days=start_offset_days),
        end_date=now + timedelta(days=end_offset_days),
        location="Surabaya Convention Center",
        max_capacity=max_capacity,
    )


def add_category(
    event: Event,
    name: str = "Regular",
    price: float = 100_000,
    quota: int = 50,
    sales_start_offset: int = -5,
    sales_end_offset: int = 5,
) -> TicketCategory:
    now = datetime.utcnow()
    return event.add_ticket_category(
        name=name,
        price=Money.of(price),
        quota=quota,
        sales_start=now + timedelta(days=sales_start_offset),
        sales_end=now + timedelta(days=sales_end_offset),
    )


def make_published_event(max_capacity: int = 100, quota: int = 50) -> Event:
    event = make_event(max_capacity=max_capacity)
    add_category(event, quota=quota)
    event.publish()
    return event


def make_paid_booking(event: Event | None = None, quantity: int = 2) -> Booking:
    if event is None:
        event = make_published_event()
    category = event.get_active_categories()[0]
    booking = Booking.create(
        customer_id=uuid4(),
        event_id=event.id,
        category_id=category.id,
        quantity=quantity,
        unit_price=category.price,
        payment_deadline_minutes=60,
    )
    booking.pay(booking.total_price)
    return booking


def make_active_ticket(booking: Booking | None = None) -> Ticket:
    if booking is None:
        booking = make_paid_booking()
    return Ticket.issue(
        booking_id=booking.id,
        customer_id=booking.customer_id,
        event_id=booking.event_id,
        category_id=booking.category_id,
    )


# =============================================================================
# 1. Money Value Object
# =============================================================================

class TestMoney:
    def test_create_valid_money(self):
        m = Money.of(50_000, "IDR")
        assert m.amount == Decimal("50000")
        assert m.currency == "IDR"

    def test_money_cannot_be_negative(self):
        with pytest.raises(ValueError, match="cannot be negative"):
            Money.of(-1, "IDR")

    def test_money_add_same_currency(self):
        a = Money.of(100_000)
        b = Money.of(50_000)
        assert a.add(b).amount == Decimal("150000")

    def test_money_add_different_currency_raises(self):
        a = Money.of(100_000, "IDR")
        b = Money.of(100, "USD")
        with pytest.raises(ValueError, match="different currencies"):
            a.add(b)

    def test_money_multiply(self):
        m = Money.of(50_000)
        assert m.multiply(3).amount == Decimal("150000")

    def test_money_currency_must_be_3_chars(self):
        with pytest.raises(ValueError, match="ISO code"):
            Money.of(1000, "RUPIAH")

    def test_money_is_immutable(self):
        m = Money.of(100_000)
        with pytest.raises(Exception):
            m.amount = Decimal("999")


# =============================================================================
# 2. Event Aggregate
# =============================================================================

class TestEventCreation:
    def test_create_event_success(self):
        event = make_event()
        assert event.status == EventStatus.DRAFT

    def test_create_event_raises_event_created_domain_event(self):
        event = make_event()
        assert any(isinstance(e, EventCreated) for e in event.pull_domain_events())

    # --- Minimum test cases ---

    def test_event_cannot_be_created_with_end_before_start(self):
        """TC-01: End date lebih awal dari start date."""
        now = datetime.utcnow()
        with pytest.raises(ValueError, match="End date must be after start date"):
            Event.create(
                organizer_id=uuid4(), name="Bad", description="",
                start_date=now + timedelta(days=5),
                end_date=now + timedelta(days=2),
                location="X", max_capacity=100,
            )

    def test_event_cannot_be_created_with_same_start_and_end(self):
        """TC-02: End date sama dengan start date."""
        now = datetime.utcnow()
        with pytest.raises(ValueError):
            Event.create(
                organizer_id=uuid4(), name="Same", description="",
                start_date=now + timedelta(days=5),
                end_date=now + timedelta(days=5),
                location="X", max_capacity=100,
            )

    def test_event_cannot_be_created_with_zero_capacity(self):
        """TC-03: Kapasitas 0."""
        now = datetime.utcnow()
        with pytest.raises(ValueError, match="greater than zero"):
            Event.create(
                organizer_id=uuid4(), name="Zero", description="",
                start_date=now + timedelta(days=1),
                end_date=now + timedelta(days=2),
                location="X", max_capacity=0,
            )

    def test_event_cannot_be_created_with_negative_capacity(self):
        """TC-04: Kapasitas negatif."""
        now = datetime.utcnow()
        with pytest.raises(ValueError, match="greater than zero"):
            Event.create(
                organizer_id=uuid4(), name="Neg", description="",
                start_date=now + timedelta(days=1),
                end_date=now + timedelta(days=2),
                location="X", max_capacity=-10,
            )


class TestEventPublish:
    def test_publish_draft_event_with_active_category(self):
        event = make_event()
        add_category(event)
        event.publish()
        assert event.status == EventStatus.PUBLISHED

    def test_publish_raises_event_published_domain_event(self):
        event = make_event()
        add_category(event)
        event.publish()
        assert any(isinstance(e, EventPublished) for e in event.pull_domain_events())

    # --- Minimum test case ---

    def test_event_cannot_be_published_without_active_ticket_category(self):
        """TC-05: Event tanpa ticket category aktif tidak boleh dipublish."""
        event = make_event()
        with pytest.raises(ValueError, match="at least one active ticket category"):
            event.publish()

    def test_event_cannot_be_published_if_cancelled(self):
        event = make_event()
        add_category(event)
        event.publish()
        event.cancel()
        with pytest.raises(ValueError, match="Cancelled event cannot be published"):
            event.publish()

    def test_event_cannot_be_published_if_already_published(self):
        event = make_event()
        add_category(event)
        event.publish()
        with pytest.raises(ValueError):
            event.publish()


class TestEventCancel:
    def test_cancel_published_event(self):
        event = make_published_event()
        event.cancel()
        assert event.status == EventStatus.CANCELLED

    def test_cancel_raises_event_cancelled_domain_event(self):
        event = make_published_event()
        event.cancel()
        assert any(isinstance(e, EventCancelled) for e in event.pull_domain_events())

    def test_cancel_deactivates_all_ticket_categories(self):
        event = make_event()
        add_category(event, name="Regular", quota=30)
        add_category(event, name="VIP", quota=20)
        event.publish()
        event.cancel()
        for cat in event.ticket_categories:
            assert cat.status == TicketCategoryStatus.INACTIVE

    def test_completed_event_cannot_be_cancelled(self):
        event = make_event()
        add_category(event)
        event.publish()
        event.status = EventStatus.COMPLETED
        with pytest.raises(ValueError, match="Completed event cannot be cancelled"):
            event.cancel()


# =============================================================================
# 3. Ticket Category
# =============================================================================

class TestTicketCategory:
    # --- Minimum test case ---

    def test_ticket_category_quota_cannot_exceed_event_capacity(self):
        """TC-06: Quota melebihi max_capacity."""
        event = make_event(max_capacity=50)
        with pytest.raises(ValueError, match="exceed maximum event capacity"):
            add_category(event, quota=60)

    def test_ticket_category_quota_sum_cannot_exceed_capacity(self):
        """TC-07: Total quota dua kategori melebihi kapasitas."""
        event = make_event(max_capacity=50)
        add_category(event, name="Regular", quota=40)
        with pytest.raises(ValueError, match="exceed maximum event capacity"):
            add_category(event, name="VIP", quota=20)

    def test_ticket_category_price_cannot_be_negative(self):
        event = make_event()
        now = datetime.utcnow()
        with pytest.raises(ValueError, match="cannot be negative"):
            event.add_ticket_category(
                name="Cheap", price=Money.of(-1000), quota=10,
                sales_start=now - timedelta(days=1),
                sales_end=now + timedelta(days=5),
            )

    def test_ticket_category_quota_must_be_positive(self):
        event = make_event()
        now = datetime.utcnow()
        with pytest.raises(ValueError):
            event.add_ticket_category(
                name="Empty", price=Money.of(100_000), quota=0,
                sales_start=now - timedelta(days=1),
                sales_end=now + timedelta(days=5),
            )

    def test_ticket_category_sales_end_must_be_before_event_start(self):
        event = make_event(start_offset_days=10)
        now = datetime.utcnow()
        with pytest.raises(ValueError, match="Sales period must end before"):
            event.add_ticket_category(
                name="Late", price=Money.of(100_000), quota=10,
                sales_start=now - timedelta(days=1),
                sales_end=now + timedelta(days=11),
            )

    def test_add_ticket_category_raises_domain_event(self):
        event = make_event()
        add_category(event)
        event.pull_domain_events()
        add_category(event, name="VIP", quota=10)
        assert any(isinstance(e, TicketCategoryCreated) for e in event.pull_domain_events())

    def test_disable_ticket_category(self):
        event = make_event()
        cat = add_category(event)
        event.disable_ticket_category(cat.id)
        assert cat.status == TicketCategoryStatus.INACTIVE

    def test_disable_raises_domain_event(self):
        event = make_event()
        cat = add_category(event)
        event.pull_domain_events()
        event.disable_ticket_category(cat.id)
        assert any(isinstance(e, TicketCategoryDisabled) for e in event.pull_domain_events())

    def test_disable_category_on_completed_event_raises(self):
        event = make_published_event()
        cat = event.ticket_categories[0]
        event.status = EventStatus.COMPLETED
        with pytest.raises(ValueError, match="completed event"):
            event.disable_ticket_category(cat.id)

    def test_ticket_category_remaining_quota(self):
        event = make_event()
        cat = add_category(event, quota=50)
        cat.reserve(10)
        assert cat.remaining_quota == 40

    def test_ticket_category_reserve_more_than_available_raises(self):
        event = make_event()
        cat = add_category(event, quota=10)
        with pytest.raises(ValueError, match="Not enough remaining quota"):
            cat.reserve(11)

    def test_inactive_category_cannot_be_reserved(self):
        event = make_event()
        cat = add_category(event)
        cat.disable()
        with pytest.raises(ValueError, match="not active"):
            cat.reserve(1)


# =============================================================================
# 4. Booking Aggregate
# =============================================================================

class TestBookingCreation:
    # --- Minimum test case ---

    def test_booking_cannot_be_created_with_zero_quantity(self):
        """TC-08: Quantity 0."""
        event = make_published_event()
        cat = event.get_active_categories()[0]
        with pytest.raises(ValueError, match="greater than zero"):
            Booking.create(
                customer_id=uuid4(), event_id=event.id,
                category_id=cat.id, quantity=0, unit_price=cat.price,
            )

    def test_booking_cannot_be_created_with_negative_quantity(self):
        event = make_published_event()
        cat = event.get_active_categories()[0]
        with pytest.raises(ValueError, match="greater than zero"):
            Booking.create(
                customer_id=uuid4(), event_id=event.id,
                category_id=cat.id, quantity=-3, unit_price=cat.price,
            )

    def test_new_booking_status_is_pending_payment(self):
        event = make_published_event()
        cat = event.get_active_categories()[0]
        booking = Booking.create(
            customer_id=uuid4(), event_id=event.id,
            category_id=cat.id, quantity=2, unit_price=cat.price,
        )
        assert booking.status == BookingStatus.PENDING_PAYMENT

    def test_booking_creation_raises_ticket_reserved_domain_event(self):
        event = make_published_event()
        cat = event.get_active_categories()[0]
        booking = Booking.create(
            customer_id=uuid4(), event_id=event.id,
            category_id=cat.id, quantity=2, unit_price=cat.price,
        )
        assert any(isinstance(e, TicketReserved) for e in booking.pull_domain_events())

    def test_booking_total_price_includes_service_fee(self):
        event = make_published_event()
        cat = event.get_active_categories()[0]
        fee = Money.of(5_000)
        booking = Booking.create(
            customer_id=uuid4(), event_id=event.id,
            category_id=cat.id, quantity=2,
            unit_price=Money.of(100_000), service_fee=fee,
        )
        assert booking.total_price.amount == Decimal("205000")

    def test_booking_total_price_cannot_be_negative(self):
        event = make_published_event()
        cat = event.get_active_categories()[0]
        booking = Booking.create(
            customer_id=uuid4(), event_id=event.id,
            category_id=cat.id, quantity=1, unit_price=Money.of(0),
        )
        assert booking.total_price.amount >= Decimal("0")


class TestBookingDomainService:
    def test_booking_cannot_be_created_for_unpublished_event(self):
        event = make_event()
        add_category(event)
        cat = event.ticket_categories[0]
        with pytest.raises(ValueError, match="Published event"):
            BookingDomainService.create_booking(
                customer_id=uuid4(), event=event,
                category_id=cat.id, quantity=1,
            )

    def test_booking_cannot_exceed_remaining_quota(self):
        event = make_published_event(quota=5)
        cat = event.get_active_categories()[0]
        with pytest.raises(ValueError, match="Not enough remaining quota"):
            BookingDomainService.create_booking(
                customer_id=uuid4(), event=event,
                category_id=cat.id, quantity=10,
            )

    def test_booking_outside_sales_period_raises(self):
        event = make_event(max_capacity=100)
        now = datetime.utcnow()
        event.add_ticket_category(
            name="Expired Sales", price=Money.of(100_000), quota=50,
            sales_start=now - timedelta(days=5),
            sales_end=now - timedelta(days=1),
        )
        event.publish()
        cat = event.ticket_categories[0]
        with pytest.raises(ValueError, match="sales period has ended"):
            BookingDomainService.create_booking(
                customer_id=uuid4(), event=event,
                category_id=cat.id, quantity=1,
            )


class TestBookingPayment:
    # --- Minimum test cases ---

    def test_booking_cannot_be_paid_after_payment_deadline(self):
        """TC-09: Deadline sudah lewat."""
        event = make_published_event()
        cat = event.get_active_categories()[0]
        booking = Booking.create(
            customer_id=uuid4(), event_id=event.id,
            category_id=cat.id, quantity=1, unit_price=cat.price,
            payment_deadline_minutes=0,
        )
        booking.payment_deadline = datetime.utcnow() - timedelta(seconds=1)
        with pytest.raises(ValueError, match="Payment deadline has passed"):
            booking.pay(booking.total_price)

    def test_booking_cannot_be_paid_with_incorrect_amount(self):
        """TC-10: Jumlah bayar salah."""
        event = make_published_event()
        cat = event.get_active_categories()[0]
        booking = Booking.create(
            customer_id=uuid4(), event_id=event.id,
            category_id=cat.id, quantity=2, unit_price=cat.price,
            payment_deadline_minutes=60,
        )
        with pytest.raises(ValueError, match="does not match total price"):
            booking.pay(Money.of(1))

    def test_booking_pay_success_changes_status_to_paid(self):
        event = make_published_event()
        cat = event.get_active_categories()[0]
        booking = Booking.create(
            customer_id=uuid4(), event_id=event.id,
            category_id=cat.id, quantity=1, unit_price=cat.price,
            payment_deadline_minutes=60,
        )
        booking.pay(booking.total_price)
        assert booking.status == BookingStatus.PAID

    def test_booking_pay_raises_booking_paid_domain_event(self):
        event = make_published_event()
        cat = event.get_active_categories()[0]
        booking = Booking.create(
            customer_id=uuid4(), event_id=event.id,
            category_id=cat.id, quantity=1, unit_price=cat.price,
            payment_deadline_minutes=60,
        )
        booking.pull_domain_events()
        booking.pay(booking.total_price)
        assert any(isinstance(e, BookingPaid) for e in booking.pull_domain_events())

    def test_booking_cannot_be_paid_if_already_paid(self):
        booking = make_paid_booking()
        with pytest.raises(ValueError, match="PendingPayment"):
            booking.pay(booking.total_price)


class TestBookingExpiry:
    # --- Minimum test case ---

    def test_paid_booking_cannot_expire(self):
        """TC-11: Booking Paid tidak boleh di-expire."""
        booking = make_paid_booking()
        with pytest.raises(ValueError, match="Paid booking cannot be expired"):
            booking.expire()

    def test_pending_booking_can_expire(self):
        event = make_published_event()
        cat = event.get_active_categories()[0]
        booking = Booking.create(
            customer_id=uuid4(), event_id=event.id,
            category_id=cat.id, quantity=1, unit_price=cat.price,
        )
        booking.expire()
        assert booking.status == BookingStatus.EXPIRED

    def test_expire_raises_booking_expired_domain_event(self):
        event = make_published_event()
        cat = event.get_active_categories()[0]
        booking = Booking.create(
            customer_id=uuid4(), event_id=event.id,
            category_id=cat.id, quantity=1, unit_price=cat.price,
        )
        booking.pull_domain_events()
        booking.expire()
        assert any(isinstance(e, BookingExpired) for e in booking.pull_domain_events())

    def test_already_expired_booking_cannot_expire_again(self):
        event = make_published_event()
        cat = event.get_active_categories()[0]
        booking = Booking.create(
            customer_id=uuid4(), event_id=event.id,
            category_id=cat.id, quantity=1, unit_price=cat.price,
        )
        booking.expire()
        with pytest.raises(ValueError):
            booking.expire()


# =============================================================================
# 5. Ticket Aggregate
# =============================================================================

class TestTicket:
    def test_issued_ticket_status_is_active(self):
        ticket = make_active_ticket()
        assert ticket.status == TicketStatus.ACTIVE

    def test_issued_ticket_has_unique_code(self):
        booking = make_paid_booking()
        t1 = make_active_ticket(booking)
        t2 = make_active_ticket(booking)
        assert t1.ticket_code != t2.ticket_code

    # --- Minimum test case ---

    def test_checked_in_ticket_cannot_be_checked_in_again(self):
        """TC-12: Tiket yang sudah check-in tidak bisa check-in lagi."""
        ticket = make_active_ticket()
        ticket.check_in(ticket.event_id)
        with pytest.raises(ValueError, match="already been checked in"):
            ticket.check_in(ticket.event_id)

    def test_check_in_changes_status_to_checked_in(self):
        ticket = make_active_ticket()
        ticket.check_in(ticket.event_id)
        assert ticket.status == TicketStatus.CHECKED_IN

    def test_check_in_raises_ticket_checked_in_domain_event(self):
        ticket = make_active_ticket()
        ticket.check_in(ticket.event_id)
        assert any(isinstance(e, TicketCheckedIn) for e in ticket.pull_domain_events())

    def test_check_in_wrong_event_raises(self):
        ticket = make_active_ticket()
        with pytest.raises(ValueError, match="does not belong to this event"):
            ticket.check_in(uuid4())

    def test_cancelled_ticket_cannot_be_checked_in(self):
        ticket = make_active_ticket()
        ticket.cancel()
        with pytest.raises(ValueError, match="Only Active tickets"):
            ticket.check_in(ticket.event_id)

    def test_checked_in_ticket_cannot_be_cancelled(self):
        ticket = make_active_ticket()
        ticket.check_in(ticket.event_id)
        with pytest.raises(ValueError, match="Checked-in ticket cannot be cancelled"):
            ticket.cancel()

    def test_active_ticket_can_be_cancelled(self):
        ticket = make_active_ticket()
        ticket.cancel()
        assert ticket.status == TicketStatus.CANCELLED

    def test_check_in_records_timestamp(self):
        ticket = make_active_ticket()
        before = datetime.utcnow()
        ticket.check_in(ticket.event_id)
        after = datetime.utcnow()
        assert ticket.checked_in_at is not None
        assert before <= ticket.checked_in_at <= after


# =============================================================================
# 6. Refund Aggregate
# =============================================================================

class TestRefundRequest:
    def test_refund_request_success(self):
        booking = make_paid_booking()
        refund = Refund.request(
            booking_id=booking.id, customer_id=booking.customer_id,
            amount=booking.total_price,
        )
        assert refund.status == RefundStatus.REQUESTED

    def test_refund_request_raises_refund_requested_domain_event(self):
        booking = make_paid_booking()
        refund = Refund.request(
            booking_id=booking.id, customer_id=booking.customer_id,
            amount=booking.total_price,
        )
        assert any(isinstance(e, RefundRequested) for e in refund.pull_domain_events())

    # --- Minimum test case ---

    def test_refund_cannot_be_requested_if_ticket_already_checked_in(self):
        """TC-13: Tiket sudah check-in → refund ditolak."""
        booking = make_paid_booking()
        ticket = make_active_ticket(booking)
        ticket.check_in(ticket.event_id)
        with pytest.raises(ValueError, match="already been checked in"):
            RefundDomainService.validate_refund_request(booking=booking, tickets=[ticket])

    def test_refund_cannot_be_requested_for_non_paid_booking(self):
        event = make_published_event()
        cat = event.get_active_categories()[0]
        booking = Booking.create(
            customer_id=uuid4(), event_id=event.id,
            category_id=cat.id, quantity=1, unit_price=cat.price,
        )
        with pytest.raises(ValueError, match="Paid booking"):
            RefundDomainService.validate_refund_request(booking=booking, tickets=[])

    def test_refund_cannot_be_requested_after_deadline(self):
        booking = make_paid_booking()
        ticket = make_active_ticket(booking)
        past = datetime.utcnow() - timedelta(days=1)
        with pytest.raises(ValueError, match="deadline has passed"):
            RefundDomainService.validate_refund_request(
                booking=booking, tickets=[ticket], refund_deadline=past,
            )

    def test_refund_allowed_after_deadline_if_event_cancelled(self):
        """Jika event dibatalkan, deadline refund diabaikan."""
        booking = make_paid_booking()
        ticket = make_active_ticket(booking)
        past = datetime.utcnow() - timedelta(days=1)
        # Tidak boleh raise
        RefundDomainService.validate_refund_request(
            booking=booking, tickets=[ticket],
            refund_deadline=past, event_cancelled=True,
        )


class TestRefundApproval:
    # --- Minimum test case ---

    def test_refund_cannot_be_approved_if_not_in_requested_status(self):
        """TC-14: Refund Rejected tidak bisa diapprove."""
        booking = make_paid_booking()
        refund = Refund.request(
            booking_id=booking.id, customer_id=booking.customer_id,
            amount=booking.total_price,
        )
        refund.reject("Not eligible")
        with pytest.raises(ValueError, match="can only be approved when status is Requested"):
            refund.approve()

    def test_refund_cannot_be_approved_if_already_approved(self):
        booking = make_paid_booking()
        refund = Refund.request(
            booking_id=booking.id, customer_id=booking.customer_id,
            amount=booking.total_price,
        )
        refund.approve()
        with pytest.raises(ValueError, match="can only be approved"):
            refund.approve()

    def test_refund_approve_changes_status(self):
        booking = make_paid_booking()
        refund = Refund.request(
            booking_id=booking.id, customer_id=booking.customer_id,
            amount=booking.total_price,
        )
        refund.approve()
        assert refund.status == RefundStatus.APPROVED

    def test_refund_approve_raises_domain_event(self):
        booking = make_paid_booking()
        refund = Refund.request(
            booking_id=booking.id, customer_id=booking.customer_id,
            amount=booking.total_price,
        )
        refund.pull_domain_events()
        refund.approve()
        assert any(isinstance(e, RefundApproved) for e in refund.pull_domain_events())


class TestRefundRejection:
    # --- Minimum test case ---

    def test_rejected_refund_must_have_rejection_reason(self):
        """TC-15: Menolak refund tanpa alasan harus error."""
        booking = make_paid_booking()
        refund = Refund.request(
            booking_id=booking.id, customer_id=booking.customer_id,
            amount=booking.total_price,
        )
        with pytest.raises(ValueError, match="Rejection reason must be provided"):
            refund.reject("")

    def test_rejected_refund_with_whitespace_reason_raises(self):
        booking = make_paid_booking()
        refund = Refund.request(
            booking_id=booking.id, customer_id=booking.customer_id,
            amount=booking.total_price,
        )
        with pytest.raises(ValueError, match="Rejection reason must be provided"):
            refund.reject("   ")

    def test_refund_reject_success(self):
        booking = make_paid_booking()
        refund = Refund.request(
            booking_id=booking.id, customer_id=booking.customer_id,
            amount=booking.total_price,
        )
        refund.reject("Ticket already used")
        assert refund.status == RefundStatus.REJECTED
        assert refund.rejection_reason == "Ticket already used"

    def test_refund_reject_raises_domain_event(self):
        booking = make_paid_booking()
        refund = Refund.request(
            booking_id=booking.id, customer_id=booking.customer_id,
            amount=booking.total_price,
        )
        refund.pull_domain_events()
        refund.reject("Not eligible")
        assert any(isinstance(e, RefundRejected) for e in refund.pull_domain_events())

    def test_approved_refund_cannot_be_rejected(self):
        booking = make_paid_booking()
        refund = Refund.request(
            booking_id=booking.id, customer_id=booking.customer_id,
            amount=booking.total_price,
        )
        refund.approve()
        with pytest.raises(ValueError, match="can only be rejected when status is Requested"):
            refund.reject("Too late")


class TestRefundPaidOut:
    def test_refund_can_be_marked_as_paid_out(self):
        booking = make_paid_booking()
        refund = Refund.request(
            booking_id=booking.id, customer_id=booking.customer_id,
            amount=booking.total_price,
        )
        refund.approve()
        refund.mark_as_paid_out("REF-001")
        assert refund.status == RefundStatus.PAID_OUT
        assert refund.payment_reference == "REF-001"

    def test_paid_out_refund_raises_domain_event(self):
        booking = make_paid_booking()
        refund = Refund.request(
            booking_id=booking.id, customer_id=booking.customer_id,
            amount=booking.total_price,
        )
        refund.approve()
        refund.pull_domain_events()
        refund.mark_as_paid_out("REF-002")
        assert any(isinstance(e, RefundPaidOut) for e in refund.pull_domain_events())

    def test_non_approved_refund_cannot_be_paid_out(self):
        booking = make_paid_booking()
        refund = Refund.request(
            booking_id=booking.id, customer_id=booking.customer_id,
            amount=booking.total_price,
        )
        with pytest.raises(ValueError, match="can only be marked as paid out when status is Approved"):
            refund.mark_as_paid_out("REF-003")

    def test_paid_out_without_reference_raises(self):
        booking = make_paid_booking()
        refund = Refund.request(
            booking_id=booking.id, customer_id=booking.customer_id,
            amount=booking.total_price,
        )
        refund.approve()
        with pytest.raises(ValueError, match="Payment reference must be provided"):
            refund.mark_as_paid_out("")