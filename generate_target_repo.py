"""Write out the toy codebase the agent operates on: `data/target_repo/`.

The whole point of this project is a repo-aware agent, which means it needs a
real repo to be aware of. `cartlogic` is a tiny shopping-cart pricing library
(discounts, shipping, tax, loyalty points, a cart that totals them up) with
FIVE deliberately seeded, single-line bugs, each caught by exactly one failing
pytest test. The agent's job is to find and fix them.

This script writes real files to disk (not an in-memory fixture) so the target
repo is checked in alongside the code -- you can open it, read it, and run
`pytest` in it directly, with no test-time codegen magic.

    python generate_target_repo.py     # writes data/target_repo/

Run `pytest -q` inside `data/target_repo/` afterwards: it should show exactly 5
failing tests (one per seeded bug) and the rest green. That mismatch is the
whole demo -- a codebase that mostly works, with a handful of real bugs in it.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "data" / "target_repo"

# --------------------------------------------------------------------------- #
# cartlogic package
# --------------------------------------------------------------------------- #

INIT_PY = '''"""cartlogic: a tiny shopping-cart pricing library.

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
'''

SHIPPING_PY = '''"""Shipping cost.

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
'''

TAX_PY = '''"""Sales tax.

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
'''

DISCOUNTS_PY = '''"""Discounts: buy-in-bulk, and flat percentage-off promo codes.

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
'''

CART_PY = '''"""The cart itself: line items, running totals, and the final total.

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
'''

LOYALTY_PY = '''"""Loyalty points: reward customers for what they spend.

One point per whole dollar spent, rounded to the nearest dollar -- a $9.90
order should earn 10 points, not shortchange the customer down to 9.
"""

from __future__ import annotations


def loyalty_points(total: float) -> int:
    """Return loyalty points earned for a given order total."""
    # BUG: floors instead of rounding. int(total // 1) always rounds DOWN, so
    # $9.90 earns 9 points instead of the correctly-rounded 10.
    return int(total // 1)
'''

# --------------------------------------------------------------------------- #
# tests
# --------------------------------------------------------------------------- #

TEST_SHIPPING_PY = '''"""Tests for cartlogic.shipping."""

from __future__ import annotations

from cartlogic.shipping import calculate_shipping


def test_shipping_charged_below_threshold():
    assert calculate_shipping(49.99) == 5.99


def test_free_shipping_above_threshold():
    assert calculate_shipping(75.00) == 0.0


def test_shipping_charged_on_empty_cart():
    assert calculate_shipping(0.0) == 5.99


def test_free_shipping_at_exactly_threshold():
    # A cart of exactly $50.00 should qualify for free shipping.
    assert calculate_shipping(50.00) == 0.0
'''

TEST_TAX_PY = '''"""Tests for cartlogic.tax."""

from __future__ import annotations

from cartlogic.tax import calculate_tax


def test_calculate_tax_basic():
    assert calculate_tax(100.0, 0.08) == 8.0


def test_calculate_tax_zero_amount():
    assert calculate_tax(0.0) == 0.0


def test_calculate_tax_custom_rate():
    assert calculate_tax(50.0, 0.10) == 5.0


def test_calculate_tax_rounds_correctly():
    # 10.10 * 0.08 = 0.8079999999999999 (real float arithmetic). The correctly
    # ROUNDED tax is $0.81; a truncating implementation wrongly gives $0.80.
    assert calculate_tax(10.10) == 0.81
'''

TEST_DISCOUNTS_PY = '''"""Tests for cartlogic.discounts."""

from __future__ import annotations

from cartlogic.discounts import apply_bulk_discount, apply_percentage_discount, best_discount


def test_apply_bulk_discount_below_threshold():
    assert apply_bulk_discount(100.0, 5) == 0.0


def test_apply_bulk_discount_above_threshold():
    assert apply_bulk_discount(100.0, 12) == 10.0


def test_apply_percentage_discount():
    assert apply_percentage_discount(100.0, 20) == 20.0


def test_best_discount_picks_the_larger():
    # Bulk discount (10%% of 100 = 10) beats a 5%% promo code (5).
    assert best_discount(100.0, 12, percent=5) == 10.0


def test_apply_bulk_discount_at_exactly_ten():
    # Exactly 10 items should already qualify for the bulk discount.
    assert apply_bulk_discount(100.0, 10) == 10.0
'''

TEST_CART_PY = '''"""Tests for cartlogic.cart."""

from __future__ import annotations

from cartlogic.cart import Cart


def test_add_item_and_subtotal():
    cart = Cart()
    cart.add_item("Mug", 10.0, quantity=2)
    assert cart.subtotal == 20.0


def test_quantity_sums_all_line_items():
    cart = Cart()
    cart.add_item("Mug", 10.0, quantity=2)
    cart.add_item("Plate", 5.0, quantity=3)
    assert cart.quantity == 5


def test_total_with_no_discount():
    cart = Cart()
    cart.add_item("Mug", 40.0, quantity=1)
    assert cart.total() == round(cart.subtotal + cart.shipping + cart.tax, 2)


def test_total_applies_discount():
    # 12 identical $10 items qualify for the 10% bulk discount, so the total
    # must be computed on the DISCOUNTED subtotal, not the raw one.
    cart = Cart()
    cart.add_item("Widget", 10.0, quantity=12)
    expected = round(cart.subtotal - cart.discount + cart.shipping + cart.tax, 2)
    assert cart.total() == expected
'''

TEST_LOYALTY_PY = '''"""Tests for cartlogic.loyalty."""

from __future__ import annotations

from cartlogic.loyalty import loyalty_points


def test_loyalty_points_whole_dollar():
    assert loyalty_points(20.0) == 20


def test_loyalty_points_zero():
    assert loyalty_points(0.0) == 0


def test_loyalty_points_rounds_correctly():
    # $9.90 should round UP to 10 points, not floor down to 9.
    assert loyalty_points(9.90) == 10
'''

FILES = {
    "cartlogic/__init__.py": INIT_PY,
    "cartlogic/shipping.py": SHIPPING_PY,
    "cartlogic/tax.py": TAX_PY,
    "cartlogic/discounts.py": DISCOUNTS_PY,
    "cartlogic/cart.py": CART_PY,
    "cartlogic/loyalty.py": LOYALTY_PY,
    "tests/test_shipping.py": TEST_SHIPPING_PY,
    "tests/test_tax.py": TEST_TAX_PY,
    "tests/test_discounts.py": TEST_DISCOUNTS_PY,
    "tests/test_cart.py": TEST_CART_PY,
    "tests/test_loyalty.py": TEST_LOYALTY_PY,
}


def main() -> None:
    for relpath, content in FILES.items():
        path = OUT / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        print(f"Wrote {path.relative_to(ROOT)}")
    print(f"\n{len(FILES)} files written to {OUT.relative_to(ROOT)}")
    print("5 seeded bugs: shipping (>=), tax (round vs truncate), discounts (>=),")
    print("cart.total() (forgets discount), loyalty (round vs floor).")


if __name__ == "__main__":
    main()
