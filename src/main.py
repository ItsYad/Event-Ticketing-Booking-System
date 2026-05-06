"""
Main Application Entry Point
Event Ticketing & Booking System
Clean Architecture + Domain-Driven Design
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.presentation.routers import event_router, booking_router, refund_router

# ============================================================
# APPLICATION SETUP
# ============================================================

app = FastAPI(
    title="Event Ticketing & Booking System",
    description="""
## Event Ticketing & Booking System API

Proyek ini dibangun menggunakan **Clean Architecture** dan **Domain-Driven Design (DDD)**.

### Actors
- **Event Organizer** - Membuat dan mengelola event
- **Customer** - Memesan dan membayar tiket
- **Gate Officer** - Validasi tiket saat check-in
- **System Admin** - Mengelola refund payout

### Arsitektur
```
src/
├── domain/          ← Business logic (Aggregates, Value Objects, Domain Events)
├── application/     ← Use cases (Commands, Queries, Handlers)  
├── infrastructure/  ← Database, External Services
└── presentation/    ← REST API (FastAPI Routers)
```

### Domain Events yang Diimplementasikan
- EventCreated, EventPublished, EventCancelled
- TicketCategoryCreated, TicketCategoryDisabled
- TicketReserved, BookingPaid, BookingExpired
- TicketCheckedIn
- RefundRequested, RefundApproved, RefundRejected, RefundPaidOut
    """,
    version="1.0.0-week8",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS untuk development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# REGISTER ROUTERS
# ============================================================

app.include_router(event_router.router)
app.include_router(booking_router.router)
app.include_router(refund_router.router)


# ============================================================
# ROOT ENDPOINT
# ============================================================

@app.get("/", tags=["Root"])
async def root():
    return {
        "project": "Event Ticketing & Booking System",
        "version": "Week 8 - Project Structure + Domain Layer",
        "architecture": "Clean Architecture + Domain-Driven Design",
        "docs": "/docs",
        "status": "running",
        "implemented_user_stories": [
            "US1: Create Event",
            "US2: Publish Event",
            "US3: Cancel Event",
            "US4: Create Ticket Category",
            "US5: Disable Ticket Category",
            "US6: View Available Events",
            "US7: View Event Details",
            "US8: Create Ticket Booking",
            "US9: Calculate Booking Total Price",
            "US10: Pay Booking",
            "US11: Expire Booking",
            "US15: Request Refund",
            "US16: Approve Refund",
            "US17: Reject Refund",
            "US18: Mark Refund as Paid Out",
        ]
    }


@app.get("/health", tags=["Root"])
async def health_check():
    return {"status": "healthy", "week": 8}
