"""US2 — full mouse support, additive to keyboard (FR-008..011, SC-002/006).

Drives the Showcase changelist with the mouse (clicks/double-clicks/offsets) and
asserts every affordance mirrors its keyboard binding, and that a mouse-only and
a keyboard-only path reach the same end state. Keyboard-only completion covers
SC-006 (operable with mouse reporting disabled).
"""

from __future__ import annotations

import pytest
from textual.widgets import DataTable

from admin_tui._internal.session import TuiSession
from admin_tui.app import AdminTuiApp
from admin_tui.screens.change import ChangeScreen
from admin_tui.screens.changelist import ChangelistScreen
from sample_project.library.models import Showcase


async def _click_showcase_in_index(pilot) -> None:
    from textual.widgets import ListView

    list_view = pilot.app.screen.query_one("#index-list", ListView)
    target = None
    for child in list_view.children:
        if getattr(child, "model", None) is Showcase:
            target = child
            break
    assert target is not None
    await pilot.click(target)
    await pilot.pause()


async def _keyboard_open_showcase(pilot) -> None:
    from textual.widgets import ListView

    list_view = pilot.app.screen.query_one("#index-list", ListView)
    idx = next(
        i
        for i, c in enumerate(list_view.children)
        if getattr(c, "model", None) is Showcase
    )
    await pilot.press("down")
    for _ in range(idx):
        await pilot.press("down")
    await pilot.press("enter")
    await pilot.pause()


@pytest.mark.django_db
async def test_mouse_click_navigates_index_to_changelist(superuser, showcases):
    session = TuiSession(user=superuser, app_class=AdminTuiApp)
    async with AdminTuiApp(session=session).run_test(size=(120, 30)) as pilot:
        await pilot.pause()
        await _click_showcase_in_index(pilot)
        assert isinstance(pilot.app.screen, ChangelistScreen)
        assert pilot.app.screen.overlay.model_admin.model is Showcase


@pytest.mark.django_db
async def test_mouse_checkbox_toggles_selection(superuser, showcases):
    session = TuiSession(user=superuser, app_class=AdminTuiApp)
    async with AdminTuiApp(session=session).run_test(size=(120, 30)) as pilot:
        await pilot.pause()
        await _click_showcase_in_index(pilot)
        screen = pilot.app.screen
        assert not screen.selected_pks
        # Click the selection column (x≈1) of the first data row (y=1; y=0 is header).
        await pilot.click("#changelist-table", offset=(1, 1))
        await pilot.pause()
        assert len(screen.selected_pks) == 1


@pytest.mark.django_db
async def test_mouse_header_click_sorts(superuser, showcases):
    session = TuiSession(user=superuser, app_class=AdminTuiApp)
    async with AdminTuiApp(session=session).run_test(size=(120, 30)) as pilot:
        await pilot.pause()
        await _click_showcase_in_index(pilot)
        screen = pilot.app.screen
        assert "o" not in screen.query_params
        # Click a data-column header (y=0, x past the 3-wide selection column).
        await pilot.click("#changelist-table", offset=(6, 0))
        await pilot.pause()
        assert "o" in screen.query_params  # a sort was applied via mouse


@pytest.mark.django_db
async def test_mouse_add_button_opens_add_form(superuser, showcases):
    session = TuiSession(user=superuser, app_class=AdminTuiApp)
    async with AdminTuiApp(session=session).run_test(size=(120, 30)) as pilot:
        await pilot.pause()
        await _click_showcase_in_index(pilot)
        await pilot.click("#add-button")
        await pilot.pause()
        assert isinstance(pilot.app.screen, ChangeScreen)
        assert pilot.app.screen.mode == "add"


@pytest.mark.django_db
async def test_mouse_double_click_opens_detail(superuser, showcases):
    session = TuiSession(user=superuser, app_class=AdminTuiApp)
    async with AdminTuiApp(session=session).run_test(size=(120, 30)) as pilot:
        await pilot.pause()
        await _click_showcase_in_index(pilot)
        # Double-click a row body (x past the selection column) opens detail.
        await pilot.click("#changelist-table", offset=(8, 1), times=2)
        await pilot.pause()
        assert isinstance(pilot.app.screen, ChangeScreen)


@pytest.mark.django_db
async def test_wheel_scroll_does_not_change_selection(superuser, showcases):
    session = TuiSession(user=superuser, app_class=AdminTuiApp)
    async with AdminTuiApp(session=session).run_test(size=(120, 30)) as pilot:
        await pilot.pause()
        await _click_showcase_in_index(pilot)
        screen = pilot.app.screen
        # Select one row, then scroll — selection must persist (FR-009).
        await pilot.click("#changelist-table", offset=(1, 1))
        await pilot.pause()
        selected_before = set(screen.selected_pks)
        table = pilot.app.screen.query_one("#changelist-table", DataTable)
        table.scroll_down()
        await pilot.pause()
        assert set(screen.selected_pks) == selected_before


@pytest.mark.django_db
async def test_mouse_and_keyboard_reach_same_selection(superuser, showcases):
    """SC-002: mouse-only and keyboard-only paths reach the same end state."""
    # Mouse path: click the checkbox of the focused (first) row.
    session_m = TuiSession(user=superuser, app_class=AdminTuiApp)
    async with AdminTuiApp(session=session_m).run_test(size=(120, 30)) as pilot:
        await pilot.pause()
        await _click_showcase_in_index(pilot)
        await pilot.click("#changelist-table", offset=(1, 1))
        await pilot.pause()
        mouse_selection = set(pilot.app.screen.selected_pks)

    # Keyboard path: Space on the first row.
    session_k = TuiSession(user=superuser, app_class=AdminTuiApp)
    async with AdminTuiApp(session=session_k).run_test(size=(120, 30)) as pilot:
        await pilot.pause()
        await _keyboard_open_showcase(pilot)
        await pilot.press("down")  # focus first row
        await pilot.press("up")
        await pilot.press("space")
        await pilot.pause()
        keyboard_selection = set(pilot.app.screen.selected_pks)

    assert mouse_selection == keyboard_selection
    assert len(mouse_selection) == 1


@pytest.mark.django_db
async def test_keyboard_only_workflow_completes(superuser, showcases):
    """SC-006: the whole flow works with no mouse at all."""
    session = TuiSession(user=superuser, app_class=AdminTuiApp)
    async with AdminTuiApp(session=session).run_test(size=(120, 30)) as pilot:
        await pilot.pause()
        await _keyboard_open_showcase(pilot)
        assert isinstance(pilot.app.screen, ChangelistScreen)
        await pilot.press("down")  # focus a row
        await pilot.press("enter")  # open detail
        await pilot.pause()
        assert isinstance(pilot.app.screen, ChangeScreen)
