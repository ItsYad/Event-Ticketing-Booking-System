"""
Pydantic Schemas untuk API Request & Response
Schema = definisi struktur data untuk validasi input/output API
"""
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, validator


# ============================================================
# EVENT SCHEMAS
# ============================================================

class CreateEventRequest(BaseModel):
    """Request body untuk membuat Event baru"""
    organizer_id: UUID
    name: str = Field(..., min_length=1, max_length=200, description="Nama event")
    description: str = Field(..., min_length=1, description="Deskripsi event")
    location: str = Field(..., min_length=1, description="Lokasi event")
    start_date: datetime = Field(..., description="Tanggal mulai event")
    end_date: datetime = Field(..., description="Tanggal selesai event")
    max_capacity: int = Field(..., gt=0, description="Kapasitas maksimal peserta")

    class Config:
        json_schema_extra = {
            "example": {
                "organizer_id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "Tech Conference 2025",
                "description": "Konferensi teknologi terbesar di Indonesia",
                "location": "Jakarta Convention Center",
                "start_date": "2025-08-15T09:00:00",
                "end_date": "2025-08-15T17:00:00",
                "max_capacity": 500
            }
        }


class CreateTicketCategoryRequest(BaseModel):
    """Request body untuk membuat Ticket Category"""
    name: str = Field(..., min_length=1, description="Nama kategori (Regular, VIP, dll)")
    price: Decimal = Field(..., ge=0, description="Harga tiket")
    currency: str = Field(default="IDR", min_length=3, max_length=3)
    quota: int = Field(..., gt=0, description="Jumlah tiket tersedia")
    sales_start_date: datetime = Field(..., description="Mulai penjualan tiket")
    sales_end_date: datetime = Field(..., description="Akhir penjualan tiket")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "VIP",
                "price": 500000,
                "currency": "IDR",
                "quota": 100,
                "sales_start_date": "2025-07-01T00:00:00",
                "sales_end_date": "2025-08-14T23:59:59"
            }
        }


class TicketCategoryResponse(BaseModel):
    """Response data untuk Ticket Category"""
    category_id: UUID
    name: str
    price: Decimal
    currency: str
    quota: int
    remaining_quota: int
    sales_start_date: datetime
    sales_end_date: datetime
    status: str


class EventResponse(BaseModel):
    """Response data untuk Event"""
    event_id: UUID
    organizer_id: UUID
    name: str
    description: str
    location: str
    start_date: datetime
    end_date: datetime
    max_capacity: int
    status: str
    ticket_categories: List[TicketCategoryResponse] = []
    lowest_price: Optional[Decimal] = None
    lowest_price_currency: Optional[str] = None


# ============================================================
# BOOKING SCHEMAS
# ============================================================

class CreateBookingRequest(BaseModel):
    """Request body untuk membuat Booking"""
    customer_id: UUID
    event_id: UUID
    category_id: UUID
    ticket_quantity: int = Field(..., gt=0, description="Jumlah tiket yang dipesan")

    class Config:
        json_schema_extra = {
            "example": {
                "customer_id": "456e4567-e89b-12d3-a456-426614174001",
                "event_id": "789e4567-e89b-12d3-a456-426614174002",
                "category_id": "abc4567-e89b-12d3-a456-426614174003",
                "ticket_quantity": 2
            }
        }


class PayBookingRequest(BaseModel):
    """Request body untuk bayar Booking"""
    payment_amount: Decimal = Field(..., gt=0, description="Jumlah pembayaran")
    currency: str = Field(default="IDR", min_length=3, max_length=3)


class TicketResponse(BaseModel):
    """Response data untuk Ticket"""
    ticket_id: UUID
    ticket_code: str
    status: str


class BookingResponse(BaseModel):
    """Response data untuk Booking"""
    booking_id: UUID
    customer_id: UUID
    event_id: UUID
    category_id: UUID
    ticket_quantity: int
    unit_price: Decimal
    currency: str
    total_price: Decimal
    payment_deadline: datetime
    status: str
    tickets: List[TicketResponse] = []


# ============================================================
# REFUND SCHEMAS
# ============================================================

class RequestRefundRequest(BaseModel):
    """Request body untuk meminta Refund"""
    booking_id: UUID
    customer_id: UUID


class RejectRefundRequest(BaseModel):
    """Request body untuk menolak Refund"""
    reason: str = Field(..., min_length=1, description="Alasan penolakan")


class MarkRefundPaidOutRequest(BaseModel):
    """Request body untuk menandai Refund sudah dibayar"""
    payment_reference: str = Field(..., min_length=1, description="Referensi pembayaran")


class RefundResponse(BaseModel):
    """Response data untuk Refund"""
    refund_id: UUID
    booking_id: UUID
    customer_id: UUID
    status: str
    rejection_reason: Optional[str] = None
    payment_reference: Optional[str] = None


# ============================================================
# COMMON SCHEMAS
# ============================================================

class MessageResponse(BaseModel):
    """Response sederhana dengan pesan"""
    message: str
    success: bool = True


class ErrorResponse(BaseModel):
    """Response untuk error"""
    error: str
    detail: Optional[str] = None
