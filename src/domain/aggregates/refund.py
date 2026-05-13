from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List
from uuid import UUID, uuid4

from src.domain.events.domain_events import (
    DomainEvent,
    RefundApproved,
    RefundPaidOut,
    RefundRejected,
    RefundRequested,
)
from src.domain.value_objects.money import Money


# ── Enum ──────────────────────────────────────────────────────────────────────

class RefundStatus(Enum):
    REQUESTED = "Requested"
    APPROVED = "Approved"
    REJECTED = "Rejected"
    PAID_OUT = "PaidOut"


# ── Aggregate Root: Refund ────────────────────────────────────────────────────

@dataclass
class Refund:
    id: UUID
    booking_id: UUID
    customer_id: UUID
    amount: Money
    status: RefundStatus
    rejection_reason: str | None = None
    payment_reference: str | None = None
    requested_at: datetime = field(default_factory=datetime.utcnow)
    _domain_events: List[DomainEvent] = field(default_factory=list, repr=False)

    # ── Factory ───────────────────────────────────────────────────────────────

    @classmethod
    def request(
        cls,
        booking_id: UUID,
        customer_id: UUID,
        amount: Money,
    ) -> "Refund":
        refund = cls(
            id=uuid4(),
            booking_id=booking_id,
            customer_id=customer_id,
            amount=amount,
            status=RefundStatus.REQUESTED,
        )
        refund._domain_events.append(
            RefundRequested(
                refund_id=refund.id,
                booking_id=booking_id,
                customer_id=customer_id,
            )
        )
        return refund

    # ── Commands ──────────────────────────────────────────────────────────────

    def approve(self) -> None:
        if self.status != RefundStatus.REQUESTED:
            raise ValueError("Refund can only be approved when status is Requested")
        self.status = RefundStatus.APPROVED
        self._domain_events.append(
            RefundApproved(refund_id=self.id, booking_id=self.booking_id)
        )

    def reject(self, reason: str) -> None:
        if self.status != RefundStatus.REQUESTED:
            raise ValueError("Refund can only be rejected when status is Requested")
        if not reason or not reason.strip():
            raise ValueError("Rejection reason must be provided")
        self.status = RefundStatus.REJECTED
        self.rejection_reason = reason
        self._domain_events.append(
            RefundRejected(
                refund_id=self.id,
                booking_id=self.booking_id,
                reason=reason,
            )
        )

    def mark_as_paid_out(self, payment_reference: str) -> None:
        if self.status != RefundStatus.APPROVED:
            raise ValueError("Refund can only be marked as paid out when status is Approved")
        if not payment_reference or not payment_reference.strip():
            raise ValueError("Payment reference must be provided")
        self.status = RefundStatus.PAID_OUT
        self.payment_reference = payment_reference
        self._domain_events.append(
            RefundPaidOut(refund_id=self.id, payment_reference=payment_reference)
        )

    # ── Queries ───────────────────────────────────────────────────────────────

    def pull_domain_events(self) -> List[DomainEvent]:
        events = list(self._domain_events)
        self._domain_events.clear()
        return events