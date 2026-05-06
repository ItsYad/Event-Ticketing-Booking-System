"""
Refund Router - REST API Endpoints untuk Refund Management
"""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status

from src.domain.aggregates.booking import BookingStatus
from src.domain.aggregates.refund import Refund
from src.domain.repositories.interfaces import IBookingRepository, IRefundRepository
from src.dependencies import get_booking_repository, get_refund_repository
from src.presentation.schemas.schemas import (
    RequestRefundRequest,
    RejectRefundRequest,
    MarkRefundPaidOutRequest,
    RefundResponse,
    MessageResponse,
)

router = APIRouter(prefix="/refunds", tags=["Refund Management"])


def _map_refund_to_response(refund: Refund) -> RefundResponse:
    return RefundResponse(
        refund_id=refund.refund_id,
        booking_id=refund.booking_id,
        customer_id=refund.customer_id,
        status=refund.status.value,
        rejection_reason=refund.rejection_reason,
        payment_reference=refund.payment_reference,
    )


@router.post("/", response_model=RefundResponse, status_code=status.HTTP_201_CREATED)
async def request_refund(
    request: RequestRefundRequest,
    booking_repo: IBookingRepository = Depends(get_booking_repository),
    refund_repo: IRefundRepository = Depends(get_refund_repository),
):
    """
    **Request Refund** (User Story 15)
    
    Customer meminta pengembalian uang untuk booking yang sudah dibayar.
    """
    booking = await booking_repo.get_by_id(request.booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking tidak ditemukan")

    if booking.customer_id != request.customer_id:
        raise HTTPException(status_code=403, detail="Bukan booking milik customer ini")

    if booking.status != BookingStatus.PAID:
        raise HTTPException(
            status_code=400,
            detail=f"Refund hanya bisa diminta untuk booking Paid. Status: {booking.status}"
        )

    if booking.has_checked_in_tickets():
        raise HTTPException(
            status_code=400,
            detail="Refund tidak bisa diminta karena ada tiket yang sudah check-in"
        )

    # Cek tidak ada refund yang sudah ada
    existing = await refund_repo.get_by_booking_id(request.booking_id)
    if existing:
        raise HTTPException(status_code=400, detail="Refund untuk booking ini sudah ada")

    refund = Refund.request(
        booking_id=request.booking_id,
        customer_id=request.customer_id,
    )
    await refund_repo.save(refund)
    return _map_refund_to_response(refund)


@router.get("/{refund_id}", response_model=RefundResponse)
async def get_refund(
    refund_id: UUID,
    refund_repo: IRefundRepository = Depends(get_refund_repository),
):
    """Ambil detail refund berdasarkan ID"""
    refund = await refund_repo.get_by_id(refund_id)
    if not refund:
        raise HTTPException(status_code=404, detail="Refund tidak ditemukan")
    return _map_refund_to_response(refund)


@router.post("/{refund_id}/approve", response_model=RefundResponse)
async def approve_refund(
    refund_id: UUID,
    refund_repo: IRefundRepository = Depends(get_refund_repository),
    booking_repo: IBookingRepository = Depends(get_booking_repository),
):
    """
    **Approve Refund** (User Story 16)
    
    Event Organizer menyetujui refund request.
    """
    refund = await refund_repo.get_by_id(refund_id)
    if not refund:
        raise HTTPException(status_code=404, detail="Refund tidak ditemukan")

    try:
        refund.approve()

        # Update booking status ke Refunded
        booking = await booking_repo.get_by_id(refund.booking_id)
        if booking:
            booking.status = BookingStatus.REFUNDED
            for ticket in booking.tickets:
                ticket.cancel()
            await booking_repo.save(booking)

        await refund_repo.save(refund)
        return _map_refund_to_response(refund)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{refund_id}/reject", response_model=RefundResponse)
async def reject_refund(
    refund_id: UUID,
    request: RejectRefundRequest,
    refund_repo: IRefundRepository = Depends(get_refund_repository),
):
    """
    **Reject Refund** (User Story 17)
    
    Event Organizer menolak refund request. Alasan wajib diisi.
    """
    refund = await refund_repo.get_by_id(refund_id)
    if not refund:
        raise HTTPException(status_code=404, detail="Refund tidak ditemukan")

    try:
        refund.reject(request.reason)
        await refund_repo.save(refund)
        return _map_refund_to_response(refund)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{refund_id}/payout", response_model=RefundResponse)
async def mark_refund_paid_out(
    refund_id: UUID,
    request: MarkRefundPaidOutRequest,
    refund_repo: IRefundRepository = Depends(get_refund_repository),
):
    """
    **Mark Refund Paid Out** (User Story 18)
    
    Admin menandai refund sudah dibayarkan ke customer.
    """
    refund = await refund_repo.get_by_id(refund_id)
    if not refund:
        raise HTTPException(status_code=404, detail="Refund tidak ditemukan")

    try:
        refund.mark_as_paid_out(request.payment_reference)
        await refund_repo.save(refund)
        return _map_refund_to_response(refund)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
