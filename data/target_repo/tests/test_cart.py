"""Tests for cartlogic.cart."""

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
