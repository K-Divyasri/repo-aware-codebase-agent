"""cartlogic: a tiny shopping-cart pricing library.

Bulk and percentage discounts, tiered shipping, sales tax, loyalty points, and
a Cart that adds it all up. Small on purpose -- it exists to be read, parsed,
and (partly) debugged by a code agent, not to be a real e-commerce backend.
"""

from __future__ import annotations

from .cart import Cart, LineItem
from .discounts import apply_bulk_discount, apply_percentage_discount, best_discount
from .loyalty import loyalty_points
from .shipping import calculate_shipping
from .tax import calculate_tax

__all__ = [
    "Cart",
    "LineItem",
    "apply_bulk_discount",
    "apply_percentage_discount",
    "best_discount",
    "loyalty_points",
    "calculate_shipping",
    "calculate_tax",
]
