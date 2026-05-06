"""
Aggregate: Ticket
Bukti kepesertaan yang dihasilkan setelah Booking dibayar.

Dipisah dari Booking karena memiliki lifecycle tersendiri:
- Punya identity unik (ticket_id, ticket_code)
- Punya state machine sendiri: Active → CheckedIn / Cancelled
- Diakses langsung oleh Gate Officer (check-in use case)

Memisahkan Ticket sebagai aggregate sendiri sesuai prinsip DDD:
"Each aggregate should be small and focused on one responsibility"
"""
from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID, uuid4

from ..events.domain_events import DomainEvent, TicketCheckedIn


class TicketStatus(str, Enum):
    """Status lifecycle sebuah Ticket"""
    ACTIVE = "Active"
    CHECKED_IN = "CheckedIn"
    CANCELLED = "Cancelled"


@dataclass
class Ticket:
    """
    Aggregate Root: Ticket

    Bukti pembelian yang dihasilkan setelah booking dibayar.
    Setiap tiket memiliki kode unik untuk validasi saat check-in.

    Business Rules:
    - Hanya bisa check-in jika status Active
    - Tidak bisa check-in dua kali
    - Tiket yang cancelled tidak bisa check-in
    """
    ticket_id: UUID
    booking_id: UUID
    event_id: UUID
    customer_id: UUID
    ticket_code: str        # Kode unik: contoh TKT-AB12CD34
    status: TicketStatus = TicketStatus.ACTIVE
    _domain_events: list = field(default_factory=list, repr=False)

    # ============================================================
    # FACTORY METHOD
    # ============================================================

    @classmethod
    def issue(
        cls,
        booking_id: UUID,
        event_id: UUID,
        customer_id: UUID,
        ticket_code: str,
    ) -> "Ticket":
        """Factory method: terbitkan tiket baru setelah booking dibayar"""
        return cls(
            ticket_id=uuid4(),
            booking_id=booking_id,
            event_id=event_id,
            customer_id=customer_id,
            ticket_code=ticket_code,
            status=TicketStatus.ACTIVE,
        )

    # ============================================================
    # COMMANDS
    # ============================================================

    def check_in(self, gate_event_id: UUID) -> None:
        """
        Check in tiket saat masuk venue.

        Business Rules:
        - Ticket harus Active
        - Event ID harus cocok (tiket milik event ini)
        - Tidak bisa check-in dua kali
        """
        if str(gate_event_id) != str(self.event_id):
            raise ValueError("Tiket tidak cocok dengan event ini")

        if self.status == TicketStatus.CHECKED_IN:
            raise ValueError("Tiket sudah pernah digunakan untuk check-in")

        if self.status != TicketStatus.ACTIVE:
            raise ValueError(
                f"Tiket tidak bisa di-check in. Status saat ini: {self.status.value}"
            )

        self.status = TicketStatus.CHECKED_IN
        self._domain_events.append(
            TicketCheckedIn(
                ticket_id=self.ticket_id,
                ticket_code=self.ticket_code,
            )
        )

    def cancel(self) -> None:
        """Batalkan tiket ini (misalnya saat refund disetujui)"""
        self.status = TicketStatus.CANCELLED

    # ============================================================
    # QUERIES
    # ============================================================

    @property
    def is_checked_in(self) -> bool:
        return self.status == TicketStatus.CHECKED_IN

    @property
    def is_active(self) -> bool:
        return self.status == TicketStatus.ACTIVE

    # ============================================================
    # DOMAIN EVENT MANAGEMENT
    # ============================================================

    def pull_domain_events(self) -> list:
        events = list(self._domain_events)
        self._domain_events.clear()
        return events
