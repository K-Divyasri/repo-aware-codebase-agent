"""Discounts: buy-in-bulk, and flat percentage-off promo codes.

Two independent discount schemes. `best_discount` is what the cart actually
uses -- it just takes whichever one saves the customer more money.
"""

from __future__ import annotations

BULK_DISCOUNT_QUANTITY = 10
BULK_DISCOUNT_RATE = 0.10


def apply_bulk_discount(subtotal: float, quantity: int) -> float:
    """Dollar amount saved by the bulk-quantity discount: 10% off at 10+ items."""
    if quantity > BULK_DISCOUNT_QUANTITY:  # BUG: should be >=, so exactly 10 items get no discount
        return round(subtotal * BULK_DISCOUNT_RATE, 2)
    return 0.0


def apply_percentage_discount(subtotal: float, percent: float | None) -> float:
    """Dollar amount saved by a flat percentage-off discount (e.g. a promo code)."""
    if not percent:
        return 0.0
    return round(subtotal * (percent / 100), 2)


def best_discount(subtotal: float, quantity: int, percent: float | None = None) -> float:
    """The larger of the bulk-quantity discount and the percentage discount.

    A customer never gets penalised for having both a promo code and a big
    enough cart -- whichever discount saves them more wins.
    """
    return max(
        apply_bulk_discount(subtotal, quantity),
        apply_percentage_discount(subtotal, percent),
    )
