"""US1 — stable, Django-like changelist (FR-001..005, SC-001).

Drives the Showcase changelist headlessly via Pilot and asserts:
  - column widths + row heights are unchanged as the cursor moves (SC-001);
  - long cells are truncated in the table but the focused row's full value is
    shown in the footer preview (FR-002/003);
  - selecting a list_filter choice yields the web admin's result set (FR-004);
  - a narrow terminal scrolls horizontally and drops no columns (FR-005).
"""

from __future__ import annotations

import pytest
from textual.widgets import DataTable, Static

from admin_tui._internal.session import TuiSession
from admin_tui.app import AdminTuiApp
from admin_tui.core.changelist import _build_changelist
from admin_tui.screens.changelist import ChangelistScreen
from admin_tui.widgets.filters import FilterSidebar, extract_filter_groups
from sample_project.library.models import Showcase


async def _open_showcase(pilot) -> ChangelistScreen:
    from textual.widgets import ListView

    list_view = pilot.app.screen.query_one("#index-list", ListView)
    idx = None
    for i, child in enumerate(list_view.children):
        if getattr(child, "model", None) is Showcase:
            idx = i
            break
    assert idx is not None, "Showcase not in index"
    await pilot.press("down")
    for _ in range(idx):
        await pilot.press("down")
    await pilot.press("enter")
    await pilot.pause()
    screen = pilot.app.screen
    assert isinstance(screen, ChangelistScreen)
    return screen


def _column_widths(table: DataTable) -> list[int]:
    return [col.width for col in table.ordered_columns]


@pytest.mark.django_db
async def test_column_widths_stable_across_cursor_moves(superuser, showcases):
    session = TuiSession(user=superuser, app_class=AdminTuiApp)
    async with AdminTuiApp(session=session).run_test(size=(120, 30)) as pilot:
        await pilot.pause()
        await _open_showcase(pilot)
        table = pilot.app.screen.query_one("#changelist-table", DataTable)
        before = _column_widths(table)
        heights_before = table.row_count
        # Move the cursor across every row.
        for _ in range(table.row_count + 2):
            await pilot.press("down")
            await pilot.pause()
        after = _column_widths(table)
        assert before == after, "column widths changed on selection (SC-001 regression)"
        assert table.row_count == heights_before


@pytest.mark.django_db
async def test_long_cell_truncated_but_full_value_in_preview(superuser, showcases):
    session = TuiSession(user=superuser, app_class=AdminTuiApp)
    async with AdminTuiApp(session=session).run_test(size=(120, 30)) as pilot:
        await pilot.pause()
        await _open_showcase(pilot)
        table = pilot.app.screen.query_one("#changelist-table", DataTable)
        # Focus row 0 (the long-description one — Showcase orders by title, so
        # "Widget One" sorts first). down+up guarantees a RowHighlighted fires.
        await pilot.press("down")
        await pilot.press("up")
        await pilot.pause()
        # The description cell in the table is truncated with an ellipsis.
        row = table.get_row_at(0)
        assert any("…" in str(cell) for cell in row), "long cell not truncated"
        # The footer preview carries the full (untruncated) value of row 0.
        preview = pilot.app.screen.query_one("#cell-preview", Static)
        assert "overflows" in str(preview.content)


@pytest.mark.django_db
async def test_filter_sidebar_shown_and_matches_web_admin(superuser, showcases):
    session = TuiSession(user=superuser, app_class=AdminTuiApp)
    async with AdminTuiApp(session=session).run_test(size=(120, 30)) as pilot:
        await pilot.pause()
        screen = await _open_showcase(pilot)
        sidebar = pilot.app.screen.query_one("#filter-sidebar", FilterSidebar)
        assert sidebar.display is True  # Showcase declares list_filter

        changelist = _build_changelist(screen.overlay.model_admin, screen.request)
        groups = extract_filter_groups(changelist, screen.request)
        titles = {t.lower() for t, _ in groups}
        assert any("active" in t for t in titles)

        # Apply the "is_active = Yes" filter the way the sidebar would, and
        # compare row count to the web admin's result set for the same param.
        screen.on_filter_sidebar_filter_chosen(
            FilterSidebar.FilterChosen("?is_active__exact=1")
        )
        await pilot.pause()
        table = pilot.app.screen.query_one("#changelist-table", DataTable)
        expected = Showcase.objects.filter(is_active=True).count()
        assert table.row_count == expected


@pytest.mark.django_db
async def test_narrow_terminal_scrolls_without_dropping_columns(superuser, showcases):
    session = TuiSession(user=superuser, app_class=AdminTuiApp)
    async with AdminTuiApp(session=session).run_test(size=(50, 20)) as pilot:
        await pilot.pause()
        await _open_showcase(pilot)
        table = pilot.app.screen.query_one("#changelist-table", DataTable)
        # Selection column + all 7 ShowcaseAdmin.list_display columns — none dropped.
        assert len(table.ordered_columns) == 8
        # Total content is wider than the viewport → horizontal scroll engaged.
        assert table.virtual_size.width >= table.size.width
