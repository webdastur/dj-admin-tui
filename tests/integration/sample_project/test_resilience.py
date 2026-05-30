"""The TUI must surface errors as notifications, never crash the app.

Reproduces the class of failure where a changelist query raises (e.g. a missing
table / OperationalError): opening the changelist must keep the app alive on a
usable screen rather than tearing down with a traceback.
"""

from __future__ import annotations

import pytest

import admin_tui.screens.changelist as changelist_mod
from admin_tui._internal.session import TuiSession
from admin_tui.app import AdminTuiApp
from admin_tui.screens.changelist import ChangelistScreen
from sample_project.library.models import Showcase


async def _open_showcase(pilot) -> None:
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
async def test_changelist_build_error_does_not_crash_app(
    superuser, showcases, monkeypatch
):
    def _boom(*args, **kwargs):
        raise RuntimeError("no such table: library_showcase")

    monkeypatch.setattr(changelist_mod, "_build_changelist", _boom)

    session = TuiSession(user=superuser, app_class=AdminTuiApp)
    async with AdminTuiApp(session=session).run_test(size=(120, 30)) as pilot:
        await pilot.pause()
        await _open_showcase(pilot)
        # The app survived: we're on the changelist screen, not a crashed app.
        assert isinstance(pilot.app.screen, ChangelistScreen)
        # And the app is still running (no unhandled exception tore it down).
        assert pilot.app.is_running


@pytest.mark.django_db
async def test_keyboard_sort_cycles_columns(superuser, showcases):
    session = TuiSession(user=superuser, app_class=AdminTuiApp)
    async with AdminTuiApp(session=session).run_test(size=(120, 30)) as pilot:
        await pilot.pause()
        await _open_showcase(pilot)
        screen = pilot.app.screen
        assert "o" not in screen.query_params
        await pilot.press("s")
        await pilot.pause()
        assert screen.query_params.get("o") == "1"  # col 1 ascending
        await pilot.press("s")
        await pilot.pause()
        assert screen.query_params.get("o") == "-1"  # col 1 descending
        await pilot.press("s")
        await pilot.pause()
        assert screen.query_params.get("o") == "2"  # advance to col 2
