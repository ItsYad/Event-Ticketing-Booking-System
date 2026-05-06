"""
Booking Router - REST API Endpoints untuk Booking Management
"""
from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status

from src.domain.aggregates.booking import Booking, BookingStatus
from src.domain.aggregates.event import EventStatus
from src.domain.value_objects.money import Money
from src.domain.repositories.interfaces import IEventRepository, IBookingRepository
from src.dependencies import get_event_repository, get_booking_repository
from src.presentation.schemas.schemas import (
    CreateBookingRequest,
    PayBookingRequest,
    BookingResponse,
    TicketResponse,
    MessageResponse,
)

router = APIRouter(prefix="/bookings", tags=["Booking Management"])


def _map_booking_to_response(booking: Booking) -> BookingResponse:
    """Helper: convert Booking aggregate ke BookingResponse schema"""
    tickets = [
        TicketResponse(
            ticket_id=t.ticket_id,
            ticket_code=t.ticket_code,
            status=t.status.value,
        )
        for t in booking.tickets
    ]
    return BookingResponse(
        booking_id=booking.booking_id,
        customer_id=booking.customer_id,
        event_id=booking.event_id,
        category_id=booking.category_id,
        ticket_quantity=booking.ticket_quantity,
        unit_price=booking.unit_price.amount,
        currency=booking.unit_price.currency,
        total_price=booking.total_price.amount,
        payment_deadline=booking.payment_deadline,
        status=booking.status.value,
        tickets=tickets,
    )


@router.post("/", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
async def create_booking(
    request: CreateBookingRequest,
    event_repo: IEventRepository = Depends(get_event_repository),
    booking_repo: IBookingRepository = Depends(get_booking_repository),
):
    """
    **Buat Booking** (User Story 8)
    
    Customer memesan tiket. Booking akan berstatus PendingPayment selama 15 menit.
    """
    # Cek event ada dan published
    event = await event_repo.get_by_id(request.event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event tidak ditemukan")
    if not event.is_published():
        raise HTTPException(status_code=400, detail="Event belum published")

    # Cek customer belum punya booking aktif untuk event ini
    existing = await booking_repo.get_by_customer_and_event(
        request.customer_id, request.event_id
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Customer sudah memiliki booking aktif untuk event ini"
        )

    # Cari ticket category
    category = None
    for tc in event.ticket_categories:
        if tc.category_id == request.category_id:
            category = tc
            break

    if not category:
        raise HTTPException(status_code=404, detail="Ticket category tidak ditemukan")

    if not category.is_active:
        raise HTTPException(status_code=400, detail="Ticket category tidak aktif")

    now = datetime.now(timezone.utc)
    if not category.is_on_sale(now):
        raise HTTPException(status_code=400, detail="Tiket tidak dalam masa penjualan")

    if request.ticket_quantity > category.remaining_quota:
        raise HTTPException(
            status_code=400,
            detail=f"Quota tidak cukup. Tersisa: {category.remaining_quota}"
        )

    try:
        # Kurangi quota
        category.reserve(request.ticket_quantity)

        # Buat booking
        booking = Booking.create(
            customer_id=request.customer_id,
            event_id=request.event_id,
            category_id=request.category_id,
            ticket_quantity=request.ticket_quantity,
            unit_price=category.price,
        )

        await booking_repo.save(booking)
        await event_repo.save(event)

        return _map_booking_to_response(booking)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{booking_id}", response_model=BookingResponse)
async def get_booking(
    booking_id: UUID,
    booking_repo: IBookingRepository = Depends(get_booking_repository),
):
    """Ambil detail booking berdasarkan ID"""
    booking = await booking_repo.get_by_id(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking tidak ditemukan")
    return _map_booking_to_response(booking)


@router.post("/{booking_id}/pay", response_model=BookingResponse)
async def pay_booking(
    booking_id: UUID,
    request: PayBookingRequest,
    booking_repo: IBookingRepository = Depends(get_booking_repository),
):
    """
    **Bayar Booking** (User Story 10)
    
    Bayar booking. Jika berhasil, tiket akan digenerate otomatis.
    """
    booking = await booking_repo.get_by_id(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking tidak ditemukan")

    try:
        payment = Money.of(float(request.payment_amount), request.currency)
        booking.pay(payment)
        await booking_repo.save(booking)
        return _map_booking_to_response(booking)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{booking_id}/expire", response_model=MessageResponse)
async def expire_booking(
    booking_id: UUID,
    booking_repo: IBookingRepository = Depends(get_booking_repository),
    event_repo: IEventRepository = Depends(get_event_repository),
):
    """
    **Expire Booking** (User Story 11)
    
    Tandai booking sebagai expired. Quota tiket akan dikembalikan.
    """
    booking = await booking_repo.get_by_id(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking tidak ditemukan")

    try:
        booking.expire()

        # Kembalikan quota ke ticket category
        event = await event_repo.get_by_id(booking.event_id)
        if event:
            for tc in event.ticket_categories:
                if tc.category_id == booking.category_id:
                    tc.release(booking.ticket_quantity)
                    await event_repo.save(event)
                    break

        await booking_repo.save(booking)
        return MessageResponse(message="Booking berhasil di-expire. Quota tiket dikembalikan.")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
