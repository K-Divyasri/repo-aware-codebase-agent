"""Tests for codeagent.parsing."""

from __future__ import annotations

from codeagent.parsing import parse_file, parse_repo


def test_parse_repo_finds_known_symbols(repo_symbols):
    names = {s.name for s in repo_symbols}
    assert "calculate_shipping" in names
    assert "Cart" in names
    assert "loyalty_points" in names


def test_symbol_kinds(repo_symbols):
    by_name = {s.name: s for s in repo_symbols}
    assert by_name["Cart"].kind == "class"
    assert by_name["calculate_shipping"].kind == "function"
    assert by_name["total"].kind == "method"


def test_symbol_has_docstring_and_code(repo_symbols):
    by_name = {s.name: s for s in repo_symbols}
    shipping = by_name["calculate_shipping"]
    assert "shipping fee" in shipping.docstring.lower()
    assert "def calculate_shipping" in shipping.code


def test_symbol_file_and_qualname_are_repo_relative(repo_symbols):
    by_name = {s.name: s for s in repo_symbols}
    cart = by_name["Cart"]
    assert cart.file == "cartlogic/cart.py"
    assert cart.qualname == "cartlogic.cart.Cart"
    total = by_name["total"]
    assert total.qualname == "cartlogic.cart.Cart.total"


def test_parse_repo_skips_pycache(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "a.py").write_text("def f():\n    pass\n", encoding="utf-8")
    cache = pkg / "__pycache__"
    cache.mkdir()
    (cache / "a.cpython-311.pyc").write_bytes(b"not python")
    symbols = parse_repo(tmp_path)
    assert all("__pycache__" not in s.file for s in symbols)
    assert any(s.name == "f" for s in symbols)


def test_parse_file_single_file(tmp_path):
    f = tmp_path / "m.py"
    f.write_text('def greet(name):\n    """Say hi."""\n    return f"hi {name}"\n', encoding="utf-8")
    symbols = parse_file(f)
    assert len(symbols) == 1
    assert symbols[0].name == "greet"
    assert symbols[0].docstring == "Say hi."
