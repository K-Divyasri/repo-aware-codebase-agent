"""Tests for cartlogic.shipping."""

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
