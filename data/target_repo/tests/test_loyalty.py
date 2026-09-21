"""Tests for cartlogic.loyalty."""

from __future__ import annotations

from cartlogic.loyalty import loyalty_points


def test_loyalty_points_whole_dollar():
    assert loyalty_points(20.0) == 20


def test_loyalty_points_zero():
    assert loyalty_points(0.0) == 0


def test_loyalty_points_rounds_correctly():
    # $9.90 should round UP to 10 points, not floor down to 9.
    assert loyalty_points(9.90) == 10
