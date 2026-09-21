"""Sales tax.

Tax is a percentage of the amount, rounded to the nearest cent -- money is
always rounded, never truncated, or customers get shortchanged by fractions of
a cent that add up.
"""

from __future__ import annotations

DEFAULT_TAX_RATE = 0.08


def calculate_tax(amount: float, rate: float = DEFAULT_TAX_RATE) -> float:
    """Return `amount * rate`, rounded to the nearest cent."""
    # BUG: truncates instead of rounding. int(x*100)/100 chops off whatever comes
    # after the second decimal instead of rounding it, so a raw tax of $0.8079999...
    # becomes $0.80 instead of the correctly-rounded $0.81.
    return int(amount * rate * 100) / 100
