"""Tests for cartlogic.discounts."""

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
