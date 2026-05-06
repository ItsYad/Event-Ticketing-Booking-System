"""
Event Router - REST API Endpoints untuk Event Management
"""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status

from src.domain.aggregates.event import Event, EventStatus
from src.domain.value_objects.money import Money
from src.domain.repositories.interfaces import IEventRepository
from src.dependencies import get_event_repository
from src.presentation.schemas.schemas import (
    CreateEventRequest,
    CreateTicketCategoryRequest,
    EventResponse,
    TicketCategoryResponse,
    MessageResponse,
)

router = APIRouter(prefix="/events", tags=["Event Management"])


def _map_event_to_response(event) -> EventResponse:
    categories = []
    for tc in event.ticket_categories:
        categories.append(TicketCategoryResponse(
            category_id=tc.category_id,
            name=tc.name,
            price=tc.price.amount,
            currency=tc.price.currency,
            quota=tc.quota,
            remaining_quota=tc.remaining_quota,
            sales_start_date=tc.sales_start_date,
            sales_end_date=tc.sales_end_date,
            status=tc.status.value,
        ))
    lowest = event.get_lowest_price()
    return EventResponse(
        event_id=event.event_id,
        organizer_id=event.organizer_id,
        name=event.name,
        description=event.description,
        location=event.location,
        start_date=event.start_date,
        end_date=event.end_date,
        max_capacity=event.max_capacity,
        status=event.status.value,
        ticket_categories=categories,
        lowest_price=lowest.amount if lowest else None,
        lowest_price_currency=lowest.currency if lowest else None,
    )


@router.post("/", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    request: CreateEventRequest,
    repo: IEventRepository = Depends(get_event_repository),
):
    """**Buat Event Baru** (User Story 1) - Status awal: Draft"""
    try:
        event = Event.create(
            organizer_id=request.organizer_id,
            name=request.name,
            description=request.description,
            location=request.location,
            start_date=request.start_date,
            end_date=request.end_date,
            max_capacity=request.max_capacity,
        )
        await repo.save(event)
        return _map_event_to_response(event)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=list[EventResponse])
async def list_published_events(repo: IEventRepository = Depends(get_event_repository)):
    """**List Event Tersedia** (User Story 6) - Hanya Published"""
    events = await repo.get_published_events()
    return [_map_event_to_response(e) for e in events]


@router.get("/{event_id}", response_model=EventResponse)
async def get_event_detail(event_id: UUID, repo: IEventRepository = Depends(get_event_repository)):
    """**Detail Event** (User Story 7)"""
    event = await repo.get_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event tidak ditemukan")
    return _map_event_to_response(event)


@router.post("/{event_id}/publish", response_model=MessageResponse)
async def publish_event(event_id: UUID, repo: IEventRepository = Depends(get_event_repository)):
    """**Publish Event** (User Story 2) - Syarat: minimal 1 ticket category aktif"""
    event = await repo.get_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event tidak ditemukan")
    try:
        event.publish()
        await repo.save(event)
        return MessageResponse(message=f"Event '{event.name}' berhasil dipublish!")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{event_id}/cancel", response_model=MessageResponse)
async def cancel_event(
    event_id: UUID,
    reason: str = "",
    repo: IEventRepository = Depends(get_event_repository),
):
    """**Cancel Event** (User Story 3)"""
    event = await repo.get_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event tidak ditemukan")
    try:
        event.cancel(reason=reason)
        await repo.save(event)
        return MessageResponse(message=f"Event '{event.name}' berhasil dibatalkan.")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{event_id}/ticket-categories", response_model=TicketCategoryResponse, status_code=201)
async def add_ticket_category(
    event_id: UUID,
    request: CreateTicketCategoryRequest,
    repo: IEventRepository = Depends(get_event_repository),
):
    """**Buat Ticket Category** (User Story 4) - Regular, VIP, Early Bird, dll"""
    event = await repo.get_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event tidak ditemukan")
    try:
        price = Money.of(float(request.price), request.currency)
        category = event.add_ticket_category(
            name=request.name,
            price=price,
            quota=request.quota,
            sales_start_date=request.sales_start_date,
            sales_end_date=request.sales_end_date,
        )
        await repo.save(event)
        return TicketCategoryResponse(
            category_id=category.category_id,
            name=category.name,
            price=category.price.amount,
            currency=category.price.currency,
            quota=category.quota,
            remaining_quota=category.remaining_quota,
            sales_start_date=category.sales_start_date,
            sales_end_date=category.sales_end_date,
            status=category.status.value,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{event_id}/ticket-categories/{category_id}/disable", response_model=MessageResponse)
async def disable_ticket_category(
    event_id: UUID,
    category_id: UUID,
    repo: IEventRepository = Depends(get_event_repository),
):
    """**Disable Ticket Category** (User Story 5)"""
    event = await repo.get_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event tidak ditemukan")
    try:
        event.disable_ticket_category(category_id)
        await repo.save(event)
        return MessageResponse(message="Ticket category berhasil dinonaktifkan.")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
