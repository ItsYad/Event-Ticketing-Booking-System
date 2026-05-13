from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List
from uuid import UUID, uuid4

from src.domain.events.domain_events import (
    DomainEvent,
    EventCancelled,
    EventCreated,
    EventPublished,
    TicketCategoryCreated,
    TicketCategoryDisabled,
)
from src.domain.value_objects.money import Money


# ── Enums ─────────────────────────────────────────────────────────────────────

class EventStatus(Enum):
    DRAFT = "Draft"
    PUBLISHED = "Published"
    CANCELLED = "Cancelled"
    COMPLETED = "Completed"


class TicketCategoryStatus(Enum):
    ACTIVE = "Active"
    INACTIVE = "Inactive"


# ── Entity: TicketCategory ────────────────────────────────────────────────────

@dataclass
class TicketCategory:
    id: UUID
    event_id: UUID
    name: str
    price: Money
    quota: int
    reserved_quota: int
    sales_start: datetime
    sales_end: datetime
    status: TicketCategoryStatus = TicketCategoryStatus.ACTIVE

    @property
    def remaining_quota(self) -> int:
        return self.quota - self.reserved_quota

    @property
    def is_on_sale(self) -> bool:
        now = datetime.utcnow()
        return (
            self.status == TicketCategoryStatus.ACTIVE
            and self.sales_start <= now <= self.sales_end
        )

    def reserve(self, quantity: int) -> None:
        if self.status != TicketCategoryStatus.ACTIVE:
            raise ValueError("Ticket category is not active")
        if quantity <= 0:
            raise ValueError("Quantity must be greater than zero")
        if quantity > self.remaining_quota:
            raise ValueError("Not enough remaining quota")
        self.reserved_quota += quantity

    def release(self, quantity: int) -> None:
        self.reserved_quota = max(0, self.reserved_quota - quantity)

    def disable(self) -> None:
        self.status = TicketCategoryStatus.INACTIVE


# ── Aggregate Root: Event ─────────────────────────────────────────────────────

@dataclass
class Event:
    id: UUID
    organizer_id: UUID
    name: str
    description: str
    start_date: datetime
    end_date: datetime
    location: str
    max_capacity: int
    status: EventStatus
    ticket_categories: List[TicketCategory] = field(default_factory=list)
    _domain_events: List[DomainEvent] = field(default_factory=list, repr=False)

    # ── Factory ───────────────────────────────────────────────────────────────

    @classmethod
    def create(
        cls,
        organizer_id: UUID,
        name: str,
        description: str,
        start_date: datetime,
        end_date: datetime,
        location: str,
        max_capacity: int,
    ) -> "Event":
        if end_date <= start_date:
            raise ValueError("End date must be after start date")
        if max_capacity <= 0:
            raise ValueError("Maximum capacity must be greater than zero")

        event = cls(
            id=uuid4(),
            organizer_id=organizer_id,
            name=name,
            description=description,
            start_date=start_date,
            end_date=end_date,
            location=location,
            max_capacity=max_capacity,
            status=EventStatus.DRAFT,
        )
        event._domain_events.append(EventCreated(event_id=event.id, name=name))
        return event

    # ── Commands ──────────────────────────────────────────────────────────────

    def publish(self) -> None:
        if self.status == EventStatus.CANCELLED:
            raise ValueError("Cancelled event cannot be published")
        if self.status != EventStatus.DRAFT:
            raise ValueError("Only Draft events can be published")
        active_categories = self.get_active_categories()
        if not active_categories:
            raise ValueError("Event must have at least one active ticket category before publishing")
        total_quota = sum(c.quota for c in active_categories)
        if total_quota > self.max_capacity:
            raise ValueError("Total ticket quota exceeds maximum event capacity")
        self.status = EventStatus.PUBLISHED
        self._domain_events.append(EventPublished(event_id=self.id))

    def cancel(self) -> None:
        if self.status == EventStatus.COMPLETED:
            raise ValueError("Completed event cannot be cancelled")
        if self.status not in (EventStatus.DRAFT, EventStatus.PUBLISHED):
            raise ValueError("Event cannot be cancelled from its current status")
        self.status = EventStatus.CANCELLED
        for category in self.ticket_categories:
            category.status = TicketCategoryStatus.INACTIVE
        self._domain_events.append(EventCancelled(event_id=self.id))

    def add_ticket_category(
        self,
        name: str,
        price: Money,
        quota: int,
        sales_start: datetime,
        sales_end: datetime,
    ) -> TicketCategory:
        if price.amount < 0:
            raise ValueError("Ticket price cannot be negative")
        if quota <= 0:
            raise ValueError("Ticket quota must be greater than zero")
        if sales_end > self.start_date:
            raise ValueError("Sales period must end before or at the event start date")
        total_existing = sum(c.quota for c in self.ticket_categories if c.status == TicketCategoryStatus.ACTIVE)
        if total_existing + quota > self.max_capacity:
            raise ValueError("Total ticket quota would exceed maximum event capacity")

        category = TicketCategory(
            id=uuid4(),
            event_id=self.id,
            name=name,
            price=price,
            quota=quota,
            reserved_quota=0,
            sales_start=sales_start,
            sales_end=sales_end,
        )
        self.ticket_categories.append(category)
        self._domain_events.append(
            TicketCategoryCreated(event_id=self.id, category_id=category.id, name=name)
        )
        return category

    def disable_ticket_category(self, category_id: UUID) -> None:
        if self.status == EventStatus.COMPLETED:
            raise ValueError("Cannot disable ticket category for a completed event")
        category = self._find_category(category_id)
        category.disable()
        self._domain_events.append(
            TicketCategoryDisabled(event_id=self.id, category_id=category_id)
        )

    # ── Queries ───────────────────────────────────────────────────────────────

    def get_active_categories(self) -> List[TicketCategory]:
        return [c for c in self.ticket_categories if c.status == TicketCategoryStatus.ACTIVE]

    def get_lowest_price(self) -> Money | None:
        active = self.get_active_categories()
        if not active:
            return None
        return min(active, key=lambda c: c.price.amount).price

    def get_category(self, category_id: UUID) -> TicketCategory:
        return self._find_category(category_id)

    def pull_domain_events(self) -> List[DomainEvent]:
        events = list(self._domain_events)
        self._domain_events.clear()
        return events

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _find_category(self, category_id: UUID) -> TicketCategory:
        for c in self.ticket_categories:
            if c.id == category_id:
                return c
        raise ValueError(f"Ticket category {category_id} not found")