"""US4 — settings-driven theming with the Django palette default (FR-015..019, SC-004/005).

Asserts the default theme is the bundled ``django``, that switching ``THEME_NAME``
changes the look but not any data behavior, and that an invalid name is rejected
before any screen is shown.
"""

from __future__ import annotations

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings

from admin_tui import conf
from admin_tui._internal.session import TuiSession
from admin_tui.app import AdminTuiApp
from admin_tui.screens.changelist import ChangelistScreen
from sample_project.library.models import Showcase


async def _open_showcase(pilot) -> ChangelistScreen:
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
    return pilot.app.screen


@pytest.mark.django_db
async def test_default_theme_is_django(superuser, showcases):
    session = TuiSession(user=superuser, app_class=AdminTuiApp)  # theme_name=None
    async with AdminTuiApp(session=session).run_test(size=(120, 30)) as pilot:
        await pilot.pause()
        assert pilot.app.theme == "django"


@pytest.mark.django_db
async def test_theme_switch_changes_look_not_data(superuser, showcases):
    # Run under the default django theme.
    session_a = TuiSession(user=superuser, app_class=AdminTuiApp)
    async with AdminTuiApp(session=session_a).run_test(size=(120, 30)) as pilot:
        await pilot.pause()
        screen = await _open_showcase(pilot)
        pks_django = set(screen._full_cells.keys())
        theme_a = pilot.app.theme

    # Run under a different (neutral) theme.
    session_b = TuiSession(
        user=superuser, app_class=AdminTuiApp, theme_name="textual-dark"
    )
    async with AdminTuiApp(session=session_b).run_test(size=(120, 30)) as pilot:
        await pilot.pause()
        screen = await _open_showcase(pilot)
        pks_neutral = set(screen._full_cells.keys())
        theme_b = pilot.app.theme

    assert theme_a == "django"
    assert theme_b == "textual-dark"
    assert theme_a != theme_b  # the look changed
    assert pks_django == pks_neutral  # the data did NOT (SC-004)
    assert pks_django == {str(s.pk) for s in Showcase.objects.all()}


@pytest.mark.django_db
def test_invalid_theme_name_rejected_before_launch(superuser):
    """SC-005: an unknown THEME_NAME fails at config load — no screen is shown."""
    with override_settings(ADMIN_TUI={"THEME_NAME": "definitely-not-a-theme"}):
        with pytest.raises(ImproperlyConfigured) as exc:
            conf._load()
    assert "THEME_NAME" in str(exc.value)
    # Restore frozen defaults.
    conf._load()
