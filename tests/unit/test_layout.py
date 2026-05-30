"""Unit tests for the changelist layout helpers (US1 / FR-001..005, SC-001).

The critical invariant: `compute_column_widths` is a pure function of
(columns, rows, caps) — there is no "selected row" input, so widths cannot
depend on selection. `truncate_cell` must be display-width aware and never
exceed the column width.
"""

from __future__ import annotations

from rich.cells import cell_len

from admin_tui.widgets.layout import (
    MAX_COL,
    MIN_COL,
    ColumnSpec,
    compute_column_widths,
    sanitize_cell,
    truncate_cell,
)


# ---- truncate_cell ---------------------------------------------------


def test_short_value_unchanged():
    assert truncate_cell("hello", 10) == "hello"


def test_overflow_is_ellipsized_and_within_width():
    out = truncate_cell("abcdefghijklmnop", 8)
    assert out.endswith("…")
    assert cell_len(out) <= 8


def test_width_one_is_just_ellipsis():
    assert truncate_cell("anything", 1) == "…"


def test_zero_width_is_empty():
    assert truncate_cell("anything", 0) == ""


def test_cjk_double_width_respects_cell_width():
    # Each CJK glyph is 2 display cells; 5 glyphs = 10 cells, truncate to 6.
    out = truncate_cell("你好世界你好", 6)
    assert cell_len(out) <= 6
    assert out.endswith("…")


def test_long_single_token_is_cut_at_boundary():
    out = truncate_cell("x" * 100, 10)
    assert cell_len(out) == 10
    assert out.endswith("…")


def test_control_chars_and_newlines_sanitized():
    assert "\n" not in truncate_cell("a\nb\tc", 20)
    assert sanitize_cell("a\x00b\x07c") == "abc"
    assert sanitize_cell("line1\nline2") == "line1 line2"


# ---- compute_column_widths -------------------------------------------


def test_width_never_below_label_length():
    specs = compute_column_widths([("k", "a-long-header-label")], rows=[])
    assert specs[0].width >= cell_len("a-long-header-label")


def test_width_clamped_to_min():
    specs = compute_column_widths([("k", "ab")], rows=[{"k": "x"}])
    assert specs[0].width == MIN_COL


def test_width_grows_with_content_up_to_max():
    rows = [{"k": "y" * 200}]
    specs = compute_column_widths([("k", "k")], rows)
    assert specs[0].width == MAX_COL


def test_width_independent_of_row_order_and_selection():
    cols = [("k", "Title")]
    rows = [{"k": "short"}, {"k": "a much longer value here"}]
    a = compute_column_widths(cols, rows)
    b = compute_column_widths(cols, list(reversed(rows)))
    # No selection input exists; order of rows must not change widths either.
    assert [s.width for s in a] == [s.width for s in b]


def test_returns_one_spec_per_column_in_order():
    specs = compute_column_widths([("a", "A"), ("b", "B"), ("c", "C")], rows=[])
    assert [s.key for s in specs] == ["a", "b", "c"]
    assert all(isinstance(s, ColumnSpec) for s in specs)
