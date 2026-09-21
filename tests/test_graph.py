"""Tests for codeagent.graph."""

from __future__ import annotations


def test_shipping_property_calls_calculate_shipping(call_graph):
    assert "calculate_shipping" in call_graph.callees("shipping")


def test_calculate_shipping_callers_include_shipping_property(call_graph):
    assert "shipping" in call_graph.callers("calculate_shipping")


def test_best_discount_calls_both_discount_functions(call_graph):
    callees = call_graph.callees("best_discount")
    assert "apply_bulk_discount" in callees
    assert "apply_percentage_discount" in callees


def test_add_item_calls_lineitem_constructor(call_graph):
    assert "LineItem" in call_graph.callees("add_item")


def test_unknown_symbol_has_no_edges(call_graph):
    assert call_graph.callers("does_not_exist") == []
    assert call_graph.callees("does_not_exist") == []
