"""
Aggregate: Refund
Mengelola proses pengembalian uang kepada customer.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
from uuid import UUID, uuid4

from ..events.domain_events import (
    DomainEvent, RefundRequested, RefundApproved, RefundRejected, RefundPaidOut
)


class RefundStatus(str, Enum):
    """Status lifecycle sebuah Refund"""
    REQUESTED = "Requested"
    APPROVED = "Approved"
    REJECTED = "Rejected"
    PAID_OUT = "PaidOut"


@dataclass
class Refund:
    """
    Aggregate Root: Refund
    Mengelola proses refund dari request hingga pembayaran.
    """
    refund_id: UUID
    booking_id: UUID
    customer_id: UUID
    status: RefundStatus = RefundStatus.REQUESTED
    rejection_reason: Optional[str] = None
    payment_reference: Optional[str] = None
    _domain_events: List[DomainEvent] = field(default_factory=list, repr=False)

    # ============================================================
    # FACTORY METHOD
    # ============================================================

    @classmethod
    def request(cls, booking_id: UUID, customer_id: UUID) -> "Refund":
        """Buat permintaan refund baru"""
        refund = cls(
            refund_id=uuid4(),
            booking_id=booking_id,
            customer_id=customer_id,
            status=RefundStatus.REQUESTED,
        )
        refund._domain_events.append(
            RefundRequested(
                refund_id=refund.refund_id,
                booking_id=booking_id,
                customer_id=customer_id,
            )
        )
        return refund

    # ============================================================
    # COMMANDS
    # ============================================================

    def approve(self) -> None:
        """
        Setujui refund request.
        Business Rule: Status harus Requested
        """
        if self.status != RefundStatus.REQUESTED:
            raise ValueError(f"Refund tidak bisa disetujui. Status saat ini: {self.status}")

        self.status = RefundStatus.APPROVED
        self._domain_events.append(RefundApproved(refund_id=self.refund_id))

    def reject(self, reason: str) -> None:
        """
        Tolak refund request.
        Business Rules:
        - Status harus Requested
        - Alasan penolakan harus ada
        """
        if self.status != RefundStatus.REQUESTED:
            raise ValueError(f"Refund tidak bisa ditolak. Status saat ini: {self.status}")

        if not reason or not reason.strip():
            raise ValueError("Alasan penolakan refund harus diisi")

        self.status = RefundStatus.REJECTED
        self.rejection_reason = reason
        self._domain_events.append(
            RefundRejected(refund_id=self.refund_id, reason=reason)
        )

    def mark_as_paid_out(self, payment_reference: str) -> None:
        """
        Tandai refund sudah dibayarkan.
        Business Rules:
        - Status harus Approved
        - Payment reference harus ada
        """
        if self.status != RefundStatus.APPROVED:
            raise ValueError(f"Refund tidak bisa di-payout. Status saat ini: {self.status}")

        if not payment_reference or not payment_reference.strip():
            raise ValueError("Payment reference harus diisi")

        self.status = RefundStatus.PAID_OUT
        self.payment_reference = payment_reference
        self._domain_events.append(
            RefundPaidOut(
                refund_id=self.refund_id,
                payment_reference=payment_reference,
            )
        )

    # ============================================================
    # DOMAIN EVENT MANAGEMENT
    # ============================================================

    def pull_domain_events(self) -> List[DomainEvent]:
        events = list(self._domain_events)
        self._domain_events.clear()
        return events
