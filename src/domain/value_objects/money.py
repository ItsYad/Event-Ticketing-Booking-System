"""
Value Object: Money
Merepresentasikan jumlah uang dengan currency.
Value Object = immutable, equality by value (bukan by identity)
"""
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)  # frozen=True = immutable (ciri khas Value Object)
class Money:
    """
    Value Object yang merepresentasikan jumlah uang.
    
    Rules:
    - Amount tidak boleh negatif
    - Currency harus 3 karakter (ISO 4217, contoh: IDR, USD)
    """
    amount: Decimal
    currency: str

    def __post_init__(self):
        """Validasi setelah inisialisasi"""
        if self.amount < Decimal("0"):
            raise ValueError("Amount tidak boleh negatif")
        if len(self.currency) != 3:
            raise ValueError("Currency harus 3 karakter (contoh: IDR, USD)")

    def add(self, other: "Money") -> "Money":
        """Tambah dua Money dengan currency yang sama"""
        if self.currency != other.currency:
            raise ValueError(f"Tidak bisa menjumlahkan {self.currency} dengan {other.currency}")
        return Money(amount=self.amount + other.amount, currency=self.currency)

    def multiply(self, quantity: int) -> "Money":
        """Kalikan amount dengan quantity"""
        if quantity < 0:
            raise ValueError("Quantity tidak boleh negatif")
        return Money(amount=self.amount * Decimal(quantity), currency=self.currency)

    def __str__(self) -> str:
        return f"{self.currency} {self.amount:,.0f}"

    @classmethod
    def zero(cls, currency: str = "IDR") -> "Money":
        """Buat Money dengan nilai 0"""
        return cls(amount=Decimal("0"), currency=currency)

    @classmethod
    def of(cls, amount: float, currency: str = "IDR") -> "Money":
        """Factory method untuk membuat Money dengan mudah"""
        return cls(amount=Decimal(str(amount)), currency=currency)
