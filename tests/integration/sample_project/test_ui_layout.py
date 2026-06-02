"""Layout regressions for the change form and changelist toolbar.

Guards three rendering bugs:

  1. View-mode read-only fields rendered as bare ``Static`` carrying the
     ``.field-row`` class (``layout: horizontal``) collapsed to height 0 — the
     value vanished and left a blank gap. They must be real ``Horizontal`` rows
     with label + value children.
  2. ``.atui-btn`` was height 3; inside the height-1 changelist toolbar the
     ``+ Add`` label (centered on the middle row) was clipped away. Buttons are
     now height 1 so the label is visible everywhere.
  3. The change-form buttons read as oversized at height 3 — now compact.
"""

from __future__ import annotations

import pytest
from textual.widgets import Button

from dj_admin_tui._internal.session import TuiSession
from dj_admin_tui.app import AdminTuiApp
from dj_admin_tui.screens.change import ChangeScreen
from dj_admin_tui.screens.changelist import ChangelistScreen

# `seeded_books` / `with_overlays` are package-level conftest fixtures (no import
# needed); `_navigate_index_to` is a plain helper imported from test_navigation.
from .test_navigation import _navigate_index_to


@pytest.mark.django_db
async def test_view_fields_render_with_values(superuser, seeded_books, with_overlays):
    session = TuiSession(user=superuser, app_class=AdminTuiApp)
    async with AdminTuiApp(session=session).run_test(size=(140, 40)) as pilot:
        await pilot.pause()
        await _navigate_index_to(pilot, "Book")
        await pilot.press("enter")  # open detail (view mode)
        await pilot.pause()
        screen = pilot.app.screen
        assert isinstance(screen, ChangeScreen)
        assert screen.mode == "view"

        values = screen.query(".field-value")
        assert len(values) > 0, "no .field-value rows rendered"
        # Regression 1: no row may collapse to height 0.
        assert all(v.size.height >= 1 for v in values), [v.size for v in values]
        # And real data must show through (not every value is the empty mark).
        texts = [str(v.render()).strip() for v in values]
        assert any(t and t != "-" for t in texts), texts

        # View mode has no focusable widgets; the scroll container must hold
        # focus so arrow / PageDown scroll a long detail.
        assert screen.query_one("#detail-body").has_focus


@pytest.mark.django_db
async def test_add_button_label_visible(superuser, seeded_books, with_overlays):
    session = TuiSession(user=superuser, app_class=AdminTuiApp)
    async with AdminTuiApp(session=session).run_test(size=(140, 40)) as pilot:
        await pilot.pause()
        await _navigate_index_to(pilot, "Book")
        await pilot.pause()
        screen = pilot.app.screen
        assert isinstance(screen, ChangelistScreen)
        add = screen.query_one("#add-button", Button)
        # Regression 2: a height-1 button fits the height-1 toolbar, label shown.
        assert add.size.height == 1, add.size
        assert add.size.width >= len("+ Add"), add.size
        assert "Add" in pilot.app.export_screenshot()


@pytest.mark.django_db
async def test_change_form_buttons_compact(superuser, seeded_books, with_overlays):
    session = TuiSession(user=superuser, app_class=AdminTuiApp)
    async with AdminTuiApp(session=session).run_test(size=(140, 40)) as pilot:
        await pilot.pause()
        await _navigate_index_to(pilot, "Book")
        await pilot.press("enter")  # view
        await pilot.pause()
        await pilot.press("e")  # edit
        await pilot.pause()
        screen = pilot.app.screen
        assert isinstance(screen, ChangeScreen)
        assert screen.mode == "edit"
        # Regression 3: every form button is a single compact row.
        for bid in ("save-button", "save-add-button", "save-continue-button", "cancel-button"):
            b = screen.query_one(f"#{bid}", Button)
            assert b.size.height == 1, (bid, b.size)
