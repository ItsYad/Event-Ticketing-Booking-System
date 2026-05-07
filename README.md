# Event Ticketing & Booking System

**Mata Kuliah:** Konstruksi Perangkat Lunak
**Institut:** Institut Teknologi Sepuluh Nopember  
**Tim:** Tim 13

| Nama                       | NRP        | Kontribusi                                                    |
| -------------------------- | ---------- | ------------------------------------------------------------- |
| Ziyad Raziq Lahitidra Afey | 5053241042 | Domain layer, business rules, unit tests, REST API            |
| Farrel Ahmad Lazuardi      | 5053241035 | Folder structure, repository interfaces, schemas, dokumentasi |

---

## Tentang Proyek

Sistem pemesanan dan pengelolaan tiket event yang dibangun menggunakan **Python** dan **FastAPI**. Arsitektur mengikuti prinsip **Clean Architecture** dan **Domain-Driven Design (DDD)**, dengan pemisahan yang jelas antara business logic, use cases, infrastruktur, dan antarmuka API.

---

## Teknologi

- Python 3.12
- FastAPI
- PostgreSQL _(Week 12, saat ini menggunakan In-Memory)_
- pytest

---

## Struktur Proyek

```
event_ticketing/
├── src/
│   ├── domain/                  # Business logic murni
│   │   ├── aggregates/
│   │   │   ├── event.py         # Aggregate: Event & TicketCategory
│   │   │   ├── booking.py       # Aggregate: Booking & Ticket
│   │   │   └── refund.py        # Aggregate: Refund
│   │   ├── value_objects/
│   │   │   └── money.py         # Value Object: Money
│   │   ├── events/
│   │   │   └── domain_events.py # Semua domain events
│   │   └── repositories/
│   │       └── interfaces.py    # Repository interfaces (abstract)
│   │
│   ├── application/             # Use cases (Week 11)
│   │   ├── commands/
│   │   ├── queries/
│   │   ├── handlers/
│   │   └── interfaces/
│   │
│   ├── infrastructure/          # Detail teknis
│   │   ├── repositories/
│   │   │   └── in_memory.py     # In-Memory repository (sementara)
│   │   └── database/            # Koneksi PostgreSQL (Week 12)
│   │
│   ├── presentation/            # REST API
│   │   ├── routers/
│   │   │   ├── event_router.py
│   │   │   ├── booking_router.py
│   │   │   └── refund_router.py
│   │   └── schemas/
│   │       └── schemas.py
│   │
│   ├── dependencies.py          # Dependency injection
│   └── main.py                  # Entry point aplikasi
│
└── tests/
    └── domain/
        └── test_domain.py       # 31 unit tests
```

---

### dokumentasi API

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## Domain Model

### Aggregates

| Aggregate | Berisi                | Keterangan                               |
| --------- | --------------------- | ---------------------------------------- |
| Event     | Event, TicketCategory | Mengelola event dan kategori tiket       |
| Booking   | Booking, Ticket       | Mengelola pemesanan dan penerbitan tiket |
| Refund    | Refund                | Mengelola proses pengembalian uang       |

### Value Objects

| Value Object | Keterangan                                                   |
| ------------ | ------------------------------------------------------------ |
| Money        | Representasi uang yang immutable, berisi amount dan currency |

### Domain Events

| Event                  | Kapan Terjadi                            |
| ---------------------- | ---------------------------------------- |
| EventCreated           | Event baru dibuat                        |
| EventPublished         | Event dipublish dan siap dijual          |
| EventCancelled         | Event dibatalkan                         |
| TicketCategoryCreated  | Ticket category ditambahkan ke event     |
| TicketCategoryDisabled | Ticket category dinonaktifkan            |
| TicketReserved         | Booking baru dibuat                      |
| BookingPaid            | Booking berhasil dibayar                 |
| BookingExpired         | Booking kadaluarsa karena tidak dibayar  |
| TicketCheckedIn        | Tiket berhasil di-check in di venue      |
| RefundRequested        | Customer mengajukan refund               |
| RefundApproved         | Refund disetujui oleh organizer          |
| RefundRejected         | Refund ditolak oleh organizer            |
| RefundPaidOut          | Uang refund sudah ditransfer ke customer |

---

## Business Rules yang Diimplementasikan

### Event

- End date tidak boleh lebih awal dari start date
- Kapasitas maksimal harus lebih dari 0
- Event hanya bisa dipublish jika ada minimal 1 ticket category aktif
- Total quota semua ticket category tidak boleh melebihi kapasitas event
- Event yang sudah Completed tidak bisa dibatalkan

### Booking

- Jumlah tiket yang dipesan harus lebih dari 0
- Booking hanya bisa dibayar selama statusnya PendingPayment
- Booking tidak bisa dibayar setelah payment deadline (15 menit)
- Jumlah pembayaran harus sama persis dengan total harga
- Booking yang sudah Paid tidak bisa di-expire

### Ticket

- Tiket hanya diterbitkan setelah booking dibayar
- Tiket yang sudah check-in tidak bisa check-in lagi
- Tiket yang dibatalkan tidak bisa check-in

### Refund

- Refund hanya bisa di-approve atau di-reject jika statusnya Requested
- Penolakan refund wajib disertai alasan
- Refund hanya bisa ditandai PaidOut jika statusnya Approved

---

## Progress Mingguan

| Week      | Status     | Keterangan                                     |
| --------- | ---------- | ---------------------------------------------- |
| Week 8    | Done       | Project structure, domain layer, unit tests    |
| Week 9-10 |            | Application layer: Commands, Queries, Handlers |
| Week 11   |            | Infrastructure layer: PostgreSQL               |
| Week 12   |            | Presentation layer: finalisasi REST API        |
| Week 13   |            | Integrasi penuh dan demo akhir                 |

---

## Arsitektur

```
Presentation  →  Application  →  Domain  ←  Infrastructure
(FastAPI)         (Use Cases)   (Logic)      (PostgreSQL)
```

Setiap layer hanya boleh bergantung ke layer yang lebih dalam. Domain layer tidak bergantung ke siapapun.
