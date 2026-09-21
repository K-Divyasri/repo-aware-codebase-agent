"""Shipping cost.

Free shipping once the subtotal reaches a threshold; a flat fee below it. The
kind of tiered rule every storefront has somewhere, and an easy place for an
off-by-one on the boundary to hide.
"""

from __future__ import annotations

FREE_SHIPPING_THRESHOLD = 50.0
FLAT_SHIPPING_FEE = 5.99


def calculate_shipping(subtotal: float) -> float:
    """Return the shipping fee for a given subtotal.

    Free shipping at or above FREE_SHIPPING_THRESHOLD; a flat FLAT_SHIPPING_FEE
    otherwise.
    """
    if subtotal > FREE_SHIPPING_THRESHOLD:  # BUG: should be >=, so exactly $50.00 wrongly gets charged
        return 0.0
    return FLAT_SHIPPING_FEE
