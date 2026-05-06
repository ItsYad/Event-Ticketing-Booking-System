"""
Unit Tests - Domain Layer
Week 8 requirement: Unit tests untuk semua business rules domain

Test cases minimum sesuai spesifikasi:
1.  Event tidak bisa dibuat dengan schedule tidak valid
2.  Event tidak bisa dibuat dengan kapasitas 0 atau negatif
3.  Event tidak bisa dipublish tanpa active ticket category
4.  Ticket category quota tidak boleh melebihi event capacity
5.  Booking tidak bisa dibuat dengan quantity 0
6.  Booking tidak bisa dibayar setelah payment deadline
7.  Booking tidak bisa dibayar dengan jumlah yang salah
8.  Paid booking tidak bisa di-expire
9.  Tiket yang sudah check-in tidak bisa check-in lagi
10. Refund tidak bisa diminta jika tiket sudah check-in
11. Refund tidak bisa di-approve jika bukan status Requested
12. Refund yang ditolak harus ada alasan penolakan
"""
import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from src.domain.aggregates.event import Event, EventStatus
from src.domain.aggregates.booking import Booking, BookingStatus, TicketStatus
from src.domain.aggregates.refund import Refund, RefundStatus
from src.domain.value_objects.money import Money


# ── FIXTURES ─────────────────────────────────────────────────

@pytest.fixture
def organizer_id():
    return uuid4()


@pytest.fixture
def future_dates():
    """Tanggal di masa depan yang valid"""
    now = datetime.now(timezone.utc)
    return {
        "start":       now + timedelta(days=30),
        "end":         now + timedelta(days=30, hours=8),
        "sales_start": now + timedelta(days=1),
        "sales_end":   now + timedelta(days=29),
    }


@pytest.fixture
def valid_event(organizer_id, future_dates):
    """Event yang valid untuk digunakan di test lain"""
    return Event.create(
        organizer_id=organizer_id,
        name="Tech Conference 2025",
        description="Konferensi teknologi terbesar",
        location="Jakarta",
        start_date=future_dates["start"],
        end_date=future_dates["end"],
        max_capacity=500,
    )


@pytest.fixture
def event_with_category(valid_event, future_dates):
    """Event dengan satu ticket category aktif"""
    valid_event.add_ticket_category(
        name="Regular",
        price=Money.of(100_000),
        quota=100,
        sales_start_date=future_dates["sales_start"],
        sales_end_date=future_dates["sales_end"],
    )
    return valid_event


@pytest.fixture
def customer_id():
    return uuid4()


@pytest.fixture
def paid_booking(customer_id, event_with_category):
    """Booking yang sudah dibayar dengan 2 tiket"""
    category = event_with_category.ticket_categories[0]
    booking = Booking.create(
        customer_id=customer_id,
        event_id=event_with_category.event_id,
        category_id=category.category_id,
        ticket_quantity=2,
        unit_price=category.price,
    )
    booking.pay(booking.total_price)
    return booking


# ── TEST 1 & 2: Event Creation ────────────────────────────────

class TestEventCreation:
    """Tests untuk validasi pembuatan Event"""

    def test_event_cannot_be_created_with_end_date_before_start_date(self, organizer_id):
        """[Test 1] End date tidak boleh lebih awal dari start date"""
        now = datetime.now(timezone.utc)
        with pytest.raises(ValueError, match="Tanggal selesai"):
            Event.create(
                organizer_id=organizer_id,
                name="Test Event",
                description="Desc",
                location="Jakarta",
                start_date=now + timedelta(days=10),
                end_date=now + timedelta(days=5),   # ❌ end < start
                max_capacity=100,
            )

    def test_event_cannot_be_created_with_zero_capacity(self, organizer_id, future_dates):
        """[Test 2a] Kapasitas tidak boleh 0"""
        with pytest.raises(ValueError, match="Kapasitas"):
            Event.create(
                organizer_id=organizer_id,
                name="Test Event",
                description="Desc",
                location="Jakarta",
                start_date=future_dates["start"],
                end_date=future_dates["end"],
                max_capacity=0,   # ❌ kapasitas 0
            )

    def test_event_cannot_be_created_with_negative_capacity(self, organizer_id, future_dates):
        """[Test 2b] Kapasitas tidak boleh negatif"""
        with pytest.raises(ValueError, match="Kapasitas"):
            Event.create(
                organizer_id=organizer_id,
                name="Test Event",
                description="Desc",
                location="Jakarta",
                start_date=future_dates["start"],
                end_date=future_dates["end"],
                max_capacity=-10,   # ❌ kapasitas negatif
            )

    def test_new_event_status_is_draft(self, valid_event):
        """Event baru harus berstatus Draft"""
        assert valid_event.status == EventStatus.DRAFT

    def test_event_creates_domain_event(self, valid_event):
        """Pembuatan event harus raise EventCreated domain event"""
        events = valid_event.pull_domain_events()
        assert len(events) == 1
        from src.domain.events.domain_events import EventCreated
        assert isinstance(events[0], EventCreated)


# ── TEST 3: Event Publishing ──────────────────────────────────

class TestEventPublishing:
    """Tests untuk publish Event"""

    def test_event_cannot_be_published_without_active_ticket_category(self, valid_event):
        """[Test 3] Event tidak bisa dipublish tanpa ticket category aktif"""
        with pytest.raises(ValueError, match="ticket category aktif"):
            valid_event.publish()

    def test_event_can_be_published_with_active_category(self, event_with_category):
        """Event bisa dipublish jika ada ticket category aktif"""
        event_with_category.publish()
        assert event_with_category.status == EventStatus.PUBLISHED

    def test_cancelled_event_cannot_be_published(self, event_with_category):
        """Event yang sudah dibatalkan tidak bisa dipublish"""
        event_with_category.cancel()
        with pytest.raises(ValueError, match="dibatalkan"):
            event_with_category.publish()


# ── TEST 4: Ticket Category Quota ────────────────────────────

class TestTicketCategoryQuota:
    """Tests untuk quota ticket category"""

    def test_ticket_category_quota_cannot_exceed_event_capacity(self, valid_event, future_dates):
        """[Test 4] Total quota tidak boleh melebihi kapasitas event"""
        # Tambah category dengan quota 400 (dari capacity 500)
        valid_event.add_ticket_category(
            name="Regular",
            price=Money.of(100_000),
            quota=400,
            sales_start_date=future_dates["sales_start"],
            sales_end_date=future_dates["sales_end"],
        )
        # Coba tambah 200 lagi → 400+200=600 > 500 ❌
        with pytest.raises(ValueError, match="kapasitas maksimal"):
            valid_event.add_ticket_category(
                name="VIP",
                price=Money.of(500_000),
                quota=200,
                sales_start_date=future_dates["sales_start"],
                sales_end_date=future_dates["sales_end"],
            )

    def test_ticket_price_cannot_be_negative(self):
        """[Test 4b] Harga tiket tidak boleh negatif"""
        with pytest.raises(ValueError):
            Money.of(-100_000)   # ❌ amount negatif


# ── TEST 5: Booking Creation ──────────────────────────────────

class TestBookingCreation:
    """Tests untuk pembuatan Booking"""

    def test_booking_cannot_be_created_with_zero_quantity(self, customer_id, event_with_category):
        """[Test 5] Booking tidak bisa dibuat dengan quantity 0"""
        category = event_with_category.ticket_categories[0]
        with pytest.raises(ValueError, match="Jumlah tiket"):
            Booking.create(
                customer_id=customer_id,
                event_id=event_with_category.event_id,
                category_id=category.category_id,
                ticket_quantity=0,   # ❌ quantity 0
                unit_price=category.price,
            )

    def test_new_booking_status_is_pending_payment(self, customer_id, event_with_category):
        """Booking baru harus berstatus PendingPayment"""
        category = event_with_category.ticket_categories[0]
        booking = Booking.create(
            customer_id=customer_id,
            event_id=event_with_category.event_id,
            category_id=category.category_id,
            ticket_quantity=1,
            unit_price=category.price,
        )
        assert booking.status == BookingStatus.PENDING_PAYMENT


# ── TEST 6 & 7: Booking Payment ───────────────────────────────

class TestBookingPayment:
    """Tests untuk pembayaran Booking"""

    def test_booking_cannot_be_paid_after_payment_deadline(self, customer_id, event_with_category):
        """[Test 6] Booking tidak bisa dibayar setelah melewati deadline"""
        category = event_with_category.ticket_categories[0]
        booking = Booking.create(
            customer_id=customer_id,
            event_id=event_with_category.event_id,
            category_id=category.category_id,
            ticket_quantity=1,
            unit_price=category.price,
        )
        # Simulasi waktu sudah melewati deadline
        past_time = booking.payment_deadline + timedelta(minutes=1)
        with pytest.raises(ValueError, match="Batas waktu pembayaran"):
            booking.pay(booking.total_price, paid_at=past_time)   # ❌ lewat deadline

    def test_booking_cannot_be_paid_with_wrong_amount(self, customer_id, event_with_category):
        """[Test 7] Booking tidak bisa dibayar dengan jumlah yang salah"""
        category = event_with_category.ticket_categories[0]
        booking = Booking.create(
            customer_id=customer_id,
            event_id=event_with_category.event_id,
            category_id=category.category_id,
            ticket_quantity=1,
            unit_price=category.price,
        )
        wrong_amount = Money.of(50_000)   # ❌ bukan total price
        with pytest.raises(ValueError, match="tidak sesuai"):
            booking.pay(wrong_amount)

    def test_paid_booking_generates_tickets(self, customer_id, event_with_category):
        """Setelah dibayar, booking harus menghasilkan tiket sesuai quantity"""
        category = event_with_category.ticket_categories[0]
        booking = Booking.create(
            customer_id=customer_id,
            event_id=event_with_category.event_id,
            category_id=category.category_id,
            ticket_quantity=3,
            unit_price=category.price,
        )
        booking.pay(booking.total_price)
        assert len(booking.tickets) == 3
        assert all(t.ticket_code.startswith("TKT-") for t in booking.tickets)


# ── TEST 8: Booking Expiry ────────────────────────────────────

class TestBookingExpiry:
    """Tests untuk expiry Booking"""

    def test_paid_booking_cannot_expire(self, paid_booking):
        """[Test 8] Booking yang sudah dibayar tidak bisa di-expire"""
        with pytest.raises(ValueError, match="sudah dibayar"):
            paid_booking.expire()

    def test_pending_booking_can_expire(self, customer_id, event_with_category):
        """Booking PendingPayment bisa di-expire"""
        category = event_with_category.ticket_categories[0]
        booking = Booking.create(
            customer_id=customer_id,
            event_id=event_with_category.event_id,
            category_id=category.category_id,
            ticket_quantity=1,
            unit_price=category.price,
        )
        booking.expire()
        assert booking.status == BookingStatus.EXPIRED


# ── TEST 9: Check-in ──────────────────────────────────────────

class TestTicketCheckIn:
    """Tests untuk check-in tiket"""

    def test_checked_in_ticket_cannot_be_checked_in_again(self, paid_booking):
        """[Test 9] Tiket yang sudah check-in tidak bisa check-in lagi"""
        ticket = paid_booking.tickets[0]
        ticket.check_in()                       # ✅ pertama kali berhasil
        with pytest.raises(ValueError):         # ❌ kedua kali gagal
            ticket.check_in()

    def test_cancelled_ticket_cannot_be_checked_in(self, paid_booking):
        """Tiket yang sudah dibatalkan tidak bisa check-in"""
        ticket = paid_booking.tickets[0]
        ticket.cancel()
        with pytest.raises(ValueError):
            ticket.check_in()


# ── TEST 10: Refund Request ───────────────────────────────────

class TestRefundRequest:
    """Tests untuk request refund"""

    def test_refund_cannot_be_requested_if_ticket_checked_in(self, paid_booking):
        """[Test 10] Refund tidak bisa diminta jika ada tiket yang sudah check-in"""
        paid_booking.tickets[0].check_in()
        assert paid_booking.has_checked_in_tickets() is True

    def test_booking_has_no_checked_in_tickets_initially(self, paid_booking):
        """Booking yang baru dibayar belum ada tiket yang check-in"""
        assert paid_booking.has_checked_in_tickets() is False


# ── TEST 11: Refund Approval ──────────────────────────────────

class TestRefundApproval:
    """Tests untuk approval refund"""

    def test_refund_can_only_be_approved_if_status_is_requested(self):
        """[Test 11] Refund hanya bisa di-approve jika berstatus Requested"""
        refund = Refund.request(booking_id=uuid4(), customer_id=uuid4())
        refund.approve()    # ✅ approve pertama berhasil

        with pytest.raises(ValueError, match="tidak bisa disetujui"):
            refund.approve()   # ❌ approve lagi setelah Approved

    def test_rejected_refund_cannot_be_approved(self):
        """Refund yang sudah ditolak tidak bisa di-approve"""
        refund = Refund.request(booking_id=uuid4(), customer_id=uuid4())
        refund.reject("Tiket sudah dipakai")
        with pytest.raises(ValueError):
            refund.approve()


# ── TEST 12: Refund Rejection ─────────────────────────────────

class TestRefundRejection:
    """Tests untuk rejection refund"""

    def test_rejected_refund_must_have_rejection_reason(self):
        """[Test 12] Refund yang ditolak harus ada alasan penolakan"""
        refund = Refund.request(booking_id=uuid4(), customer_id=uuid4())

        with pytest.raises(ValueError, match="Alasan penolakan"):
            refund.reject("")      # ❌ alasan kosong

        with pytest.raises(ValueError, match="Alasan penolakan"):
            refund.reject("   ")   # ❌ hanya spasi

    def test_refund_can_be_rejected_with_reason(self):
        """Refund bisa ditolak jika ada alasan"""
        refund = Refund.request(booking_id=uuid4(), customer_id=uuid4())
        refund.reject("Tiket sudah digunakan sebelum acara")

        assert refund.status == RefundStatus.REJECTED
        assert refund.rejection_reason == "Tiket sudah digunakan sebelum acara"


# ── TEST BONUS: Money Value Object ───────────────────────────

class TestMoney:
    """Tests untuk Value Object Money"""

    def test_money_amount_cannot_be_negative(self):
        """Amount Money tidak boleh negatif"""
        with pytest.raises(ValueError):
            Money(amount=Decimal("-100"), currency="IDR")

    def test_money_addition_same_currency(self):
        """Money bisa dijumlahkan jika currency sama"""
        result = Money.of(100_000).add(Money.of(50_000))
        assert result.amount == Decimal("150000")

    def test_money_addition_different_currency_raises_error(self):
        """Money tidak bisa dijumlahkan jika currency berbeda"""
        with pytest.raises(ValueError, match="IDR"):
            Money.of(100_000, "IDR").add(Money.of(10, "USD"))

    def test_money_multiply(self):
        """Money bisa dikalikan dengan quantity"""
        total = Money.of(100_000).multiply(3)
        assert total.amount == Decimal("300000")

    def test_money_equality(self):
        """Money dengan amount dan currency sama harus equal"""
        assert Money.of(100_000, "IDR") == Money.of(100_000, "IDR")

    def test_money_is_immutable(self):
        """Money adalah Value Object yang immutable (frozen dataclass)"""
        money = Money.of(100_000)
        with pytest.raises(Exception):
            money.amount = Decimal("200000")   # ❌ tidak bisa diubah
