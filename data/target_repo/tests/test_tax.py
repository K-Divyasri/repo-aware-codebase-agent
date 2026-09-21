"""Tests for cartlogic.tax."""

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
