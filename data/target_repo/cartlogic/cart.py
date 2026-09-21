"""The cart itself: line items, running totals, and the final total.

`Cart` is the one thing that ties discounts, shipping, and tax together, so
it's also the one place a bug can hide in the *composition* of otherwise
correct pieces, rather than in any single calculation.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .discounts import best_discount
from .shipping import calculate_shipping
from .tax import calculate_tax


@dataclass
class LineItem:
    """One line of the cart: a product, its unit price, and how many."""

    name: str
    unit_price: float
    quantity: int = 1

    @property
    def line_total(self) -> float:
        return round(self.unit_price * self.quantity, 2)


@dataclass
class Cart:
    """A shopping cart: its items, an optional promo percentage, and totals."""

    items: list[LineItem] = field(default_factory=list)
    percent_off: float | None = None

    def add_item(self, name: str, unit_price: float, quantity: int = 1) -> None:
        self.items.append(LineItem(name=name, unit_price=unit_price, quantity=quantity))

    @property
    def quantity(self) -> int:
        return sum(item.quantity for item in self.items)

    @property
    def subtotal(self) -> float:
        return round(sum(item.line_total for item in self.items), 2)

    @property
    def discount(self) -> float:
        return best_discount(self.subtotal, self.quantity, self.percent_off)

    @property
    def shipping(self) -> float:
        return calculate_shipping(self.subtotal - self.discount)

    @property
    def tax(self) -> float:
        return calculate_tax(self.subtotal - self.discount)

    def total(self) -> float:
        """Subtotal, minus the discount, plus shipping, plus tax."""
        # BUG: forgets to subtract self.discount before adding shipping and tax.
        return round(self.subtotal + self.shipping + self.tax, 2)
