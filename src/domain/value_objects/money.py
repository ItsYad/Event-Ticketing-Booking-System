from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str

    def __post_init__(self) -> None:
        if not isinstance(self.amount, Decimal):
            object.__setattr__(self, "amount", Decimal(str(self.amount)))
        if self.amount < Decimal("0"):
            raise ValueError("Money amount cannot be negative")
        if len(self.currency) != 3:
            raise ValueError("Currency must be a 3-character ISO code")

    @classmethod
    def of(cls, amount: int | float | str | Decimal, currency: str = "IDR") -> "Money":
        return cls(amount=Decimal(str(amount)), currency=currency.upper())

    def add(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise ValueError(
                f"Cannot add different currencies: {self.currency} and {other.currency}"
            )
        return Money(amount=self.amount + other.amount, currency=self.currency)

    def multiply(self, factor: int | float | Decimal) -> "Money":
        result = self.amount * Decimal(str(factor))
        if result < Decimal("0"):
            raise ValueError("Money amount cannot be negative after multiplication")
        return Money(amount=result, currency=self.currency)

    def __repr__(self) -> str:
        return f"Money({self.amount} {self.currency})"