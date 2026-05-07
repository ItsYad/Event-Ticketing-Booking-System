# Event Ticketing & Booking System
## EF234402 – Konstruksi Perangkat Lunak | Week 8

> Implementasi menggunakan **Python + FastAPI** dengan **Clean Architecture** dan **Domain-Driven Design (DDD)**

---

## Progres Week 8

Week 8 fokus pada:
1. Struktur folder Clean Architecture
2. Business rules awal dari user stories
3. Draft domain model
4. Ubiquitous Language Glossary


---

## Struktur Folder (Clean Architecture)

```
event_ticketing/
├── src/
│   ├── domain/                        ← DOMAIN LAYER (Week 9-10)
│   │   ├── aggregates/
│   │   │   ├── event.py               ← Aggregate: Event + TicketCategory
│   │   │   ├── booking.py             ← Aggregate: Booking
│   │   │   ├── ticket.py              ← Aggregate: Ticket
│   │   │   └── refund.py              ← Aggregate: Refund
│   │   ├── value_objects/
│   │   │   └── money.py               ← Value Object: Money
│   │   ├── events/
│   │   │   └── domain_events.py       ← 13 Domain Events
│   │   ├── repositories/
│   │   │   └── interfaces.py          ← Repository Interfaces (abstract)
│   │   └── services/                  ← Domain Services (jika diperlukan)
│   │
│   ├── application/                   ← APPLICATION LAYER (Week 11)
│   │   ├── commands/                  ← Command definitions
│   │   ├── queries/                   ← Query definitions
│   │   ├── handlers/                  ← Command & Query handlers
│   │   ├── interfaces/                ← External service interfaces
│   │   └── dtos/                      ← Data Transfer Objects
│   │
│   ├── infrastructure/                ← INFRASTRUCTURE LAYER (Week 12)
│   │   ├── repositories/
│   │   │   └── in_memory.py           ← Sementara In-Memory, nanti PostgreSQL
│   │   ├── database/                  ← Konfigurasi PostgreSQL
│   │   └── services/                  ← Implementasi external services
│   │
│   ├── presentation/                  ← PRESENTATION LAYER (Week 13)
│   │   ├── routers/                   ← FastAPI REST API endpoints
│   │   └── schemas/                   ← Pydantic request/response schemas
│   │
│   ├── dependencies.py                ← Dependency Injection Container
│   └── main.py                        ← FastAPI entry point
│
└── tests/
    └── domain/
        └── test_domain.py             ← Unit tests (Week 9-10)
```

---

## Dependency Rule (Clean Architecture)

```
Presentation → Application → Domain ← Infrastructure
```

- Setiap layer hanya boleh bergantung ke layer yang lebih dalam
- Domain layer tidak boleh bergantung ke layer lain
- Infrastructure mengimplementasikan interface yang didefinisikan di domain

---

## Domain Model (Draft)

### Aggregates

| Aggregate Root | Child Entities | Value Objects |
|----------------|---------------|---------------|
| Event          | TicketCategory | Money (price) |
| Booking        | —             | Money (total) |
| Ticket         | —             | —             |
| Refund         | —             | —             |

### Status Lifecycle

**Event:** Draft → Published → Cancelled / Completed

**Booking:** PendingPayment → Paid → Refunded
             PendingPayment → Expired

**Ticket:** Active → CheckedIn / Cancelled

**Refund:** Requested → Approved → PaidOut
            Requested → Rejected

### Business Rules (Initial)

**Event:**
- End date tidak boleh lebih awal dari start date
- Kapasitas maksimal harus lebih dari 0
- Event hanya bisa dipublish jika ada minimal 1 ticket category aktif
- Total quota ticket category tidak boleh melebihi kapasitas event
- Event berstatus Cancelled tidak bisa dipublish
- Event berstatus Completed tidak bisa dibatalkan

**Ticket Category:**
- Harga tidak boleh negatif
- Quota harus lebih dari 0
- Sales period harus berakhir sebelum atau saat event dimulai

**Booking:**
- Quantity harus lebih dari 0
- Tidak bisa memesan jika ticket category tidak aktif atau di luar sales period
- Satu customer hanya boleh punya satu booking aktif per event
- Payment deadline: 15 menit setelah booking dibuat
- Tidak bisa dibayar setelah payment deadline
- Jumlah pembayaran harus sama dengan total price
- Booking yang sudah Paid tidak bisa di-expire

**Refund:**
- Hanya bisa diminta untuk booking berstatus Paid
- Tidak bisa diminta jika ada tiket yang sudah check-in
- Penolakan refund harus disertai alasan

---

## Ubiquitous Language Glossary

| Term | Makna |
|------|-------|
| Event | Kegiatan yang diorganisir oleh Event Organizer |
| Event Organizer | User yang membuat dan mengelola event |
| Customer | User yang memesan dan membayar tiket |
| Gate Officer | User yang validasi tiket saat check-in |
| System Admin | User yang mengelola refund payout |
| Ticket Category | Tipe tiket: Regular, VIP, Early Bird, dll |
| Quota | Jumlah maksimal tiket per kategori |
| Booking | Reservasi sementara sebelum pembayaran |
| PendingPayment | Status booking yang belum dibayar |
| Paid | Status booking yang sudah dibayar |
| Expired | Status booking yang melewati payment deadline |
| Refunded | Status booking yang uangnya dikembalikan |
| Ticket | Bukti kepesertaan setelah booking Paid |
| Ticket Code | Kode unik (contoh: TKT-AB12CD34) untuk check-in |
| Check-in | Proses validasi tiket saat masuk venue |
| Sales Period | Periode tiket bisa dibeli |
| Payment Deadline | Batas waktu bayar (15 menit setelah booking) |
| Money | Value Object: jumlah uang + currency |
| Refund | Proses pengembalian uang ke customer |
| Domain Event | Sesuatu yang sudah terjadi di domain (past tense) |
| Aggregate | Cluster entity yang dimodifikasi sebagai satu unit |
| Aggregate Root | Satu-satunya pintu masuk untuk memodifikasi aggregate |
| Repository | Abstraksi penyimpanan data aggregate |
| Value Object | Objek immutable, equality by value bukan identity |

---

## Rencana Implementasi

| Week | Target |
|------|--------|
| Week 8  | (done) Struktur folder, business rules, domain model draft, glossary |
| Week 9-10 | Domain layer: Aggregates, Value Objects, Domain Events, Repository Interfaces, Unit Tests |
| Week 11 | Application layer: Commands, Queries, Handlers, Service Interfaces |
| Week 12 | Infrastructure layer: PostgreSQL, Repository impl, External services |
| Week 13 | Presentation layer: REST API Controllers, integrasi penuh |

---


