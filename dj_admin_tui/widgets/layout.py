"""Changelist column layout + cell truncation.

Letting Textual's ``DataTable`` auto-size columns to their widest cell and
auto-scroll horizontally to the cursor reads as "columns cropped, full text
revealed on select." Instead we compute **fixed** column widths once per
rebuild (independent of which row is selected) and pre-truncate every cell.

Both functions are pure and unit-tested in ``tests/unit/test_layout.py``. The
critical invariant: ``compute_column_widths`` output depends only on
``(columns, rows, caps)`` — never on selection/cursor state.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from rich.cells import cell_len, set_cell_size

#: Default column-width clamps (display cells).
MIN_COL = 6
MAX_COL = 40
#: Fixed width of the leading selection-indicator column.
SELECTION_WIDTH = 3

# Control characters (incl. C0/C1 and DEL) that would corrupt a single-line
# cell. Newlines/tabs/CR are handled separately (collapsed to a space).
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")


@dataclass(frozen=True)
class ColumnSpec:
    """A computed changelist column. Width is selection-independent."""

    key: str
    label: str
    width: int
    align: str = "left"


def sanitize_cell(value: object) -> str:
    """Flatten a cell value to a safe single line.

    Collapses newlines/tabs/CR to spaces and strips other control sequences so
    a value can never break the surrounding row/column layout (extends v1's
    control-sequence edge case to the truncation model).
    """
    s = "" if value is None else str(value)
    s = s.replace("\r\n", " ").replace("\n", " ").replace("\r", " ").replace("\t", " ")
    s = _CONTROL_RE.sub("", s)
    return s


def truncate_cell(value: object, width: int) -> str:
    """Truncate ``value`` to at most ``width`` display cells, ellipsizing.

    Display-width aware (CJK / emoji / zero-width) via ``rich.cells``. Always
    returns a string whose ``cell_len`` is ``<= width``. Truncation does not
    depend on selection state.
    """
    s = sanitize_cell(value)
    if width <= 0:
        return ""
    if cell_len(s) <= width:
        return s
    if width == 1:
        return "…"
    # Cut to (width - 1) display cells, then append the ellipsis. set_cell_size
    # handles double-width boundaries (pads with a space if a wide glyph would
    # be split), so the result is exactly width-1 cells before the ellipsis.
    head = set_cell_size(s, width - 1)
    return head + "…"


def compute_column_widths(
    columns: Sequence[tuple[str, str] | tuple[str, str, str]],
    rows: Iterable[Mapping[str, object]],
    *,
    min_col: int = MIN_COL,
    max_col: int = MAX_COL,
) -> list[ColumnSpec]:
    """Compute a stable width for each data column.

    Args:
        columns: ``(key, label)`` or ``(key, label, align)`` per data column
            (the leading selection column is NOT included here).
        rows: the *current page's* rendered rows as ``{column_key: value}``
            mappings. Only the current page is sampled — never the full
            queryset — so memory stays bounded by ``list_per_page``.
        min_col / max_col: width clamps in display cells.

    Returns:
        One ``ColumnSpec`` per column, in order. Width = ``clamp(widest of
        label and sampled cells, min_col, max_col)``. The result is a pure
        function of the arguments — independent of which row is selected.
    """
    materialized = list(rows)
    specs: list[ColumnSpec] = []
    for col in columns:
        key, label = col[0], col[1]
        align = col[2] if len(col) > 2 else "left"
        widest = cell_len(sanitize_cell(label))
        for row in materialized:
            widest = max(widest, cell_len(sanitize_cell(row.get(key, ""))))
        width = max(min_col, min(max_col, widest))
        specs.append(ColumnSpec(key=key, label=label, width=width, align=align))
    return specs
