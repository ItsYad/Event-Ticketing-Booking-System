"""
Dependency Injection Container
Menyediakan instance repository yang akan diinjeksikan ke routers.

Saat ini menggunakan In-Memory repository (Week 8).
Di Week 12, akan diganti dengan PostgreSQL repository.
"""
from functools import lru_cache
from src.infrastructure.repositories.in_memory import (
    InMemoryEventRepository,
    InMemoryBookingRepository,
    InMemoryRefundRepository,
    InMemoryTicketRepository,
)

# Singleton instances (shared across requests)
_event_repo = InMemoryEventRepository()
_booking_repo = InMemoryBookingRepository()
_refund_repo = InMemoryRefundRepository()
_ticket_repo = InMemoryTicketRepository()


def get_event_repository() -> InMemoryEventRepository:
    return _event_repo


def get_booking_repository() -> InMemoryBookingRepository:
    return _booking_repo


def get_refund_repository() -> InMemoryRefundRepository:
    return _refund_repo


def get_ticket_repository() -> InMemoryTicketRepository:
    return _ticket_repo
