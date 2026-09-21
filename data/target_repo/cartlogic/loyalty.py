"""Loyalty points: reward customers for what they spend.

One point per whole dollar spent, rounded to the nearest dollar -- a $9.90
order should earn 10 points, not shortchange the customer down to 9.
"""

from __future__ import annotations


def loyalty_points(total: float) -> int:
    """Return loyalty points earned for a given order total."""
    # BUG: floors instead of rounding. int(total // 1) always rounds DOWN, so
    # $9.90 earns 9 points instead of the correctly-rounded 10.
    return int(total // 1)
