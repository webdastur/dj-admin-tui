"""AdminTuiApp — the Textual App subclass. Public API (Constitution V).

Subclass to reskin or extend wholesale. Selected per-project via
`ADMIN_TUI["APP_CLASS"]` or per-invocation via `--app`. See
contracts/public-api.md § 5 for the subclass contract.

Module-level imports deliberately avoid `admin_tui.screens.*` — those are
Phase 3 territory and are loaded lazily in `on_mount()` so the package
remains importable from Phase 2 onward.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from textual.app import App

if TYPE_CHECKING:
    from admin_tui._internal.session import TuiSession


def _allow_django_orm_in_async_context() -> None:
    """Tell Django its async safety guard doesn't apply here.

    Textual runs a single-threaded asyncio event loop. Django's ORM
    raises `SynchronousOnlyOperation` from inside `async def` methods to
    prevent concurrent ORM use across worker threads — a hazard that
    cannot arise in our setup. We opt out so screen lifecycle methods
    (on_mount, key handlers) can hit the DB directly via Django's sync
    ORM, which is what every Constitution-I admin call expects.
    """
    os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")


class AdminTuiApp(App):
    """The default Textual App for the admin TUI.

    The App constructor takes a `session: TuiSession` keyword. Subclasses
    that override `__init__` MUST forward `session=` to `super()`.
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("?", "show_help", "Help"),
    ]

    def __init__(self, *, session: "TuiSession") -> None:
        _allow_django_orm_in_async_context()
        self.session = session
        # The `.tcss` override is layered on top of the selected theme; set
        # CSS_PATH before super().__init__ so Textual loads it.
        if session.theme_path is not None:
            self.CSS_PATH = str(session.theme_path)
        super().__init__()
        # Palette layer: register the bundled themes and apply the resolved
        # THEME_NAME (defaults to the bundled "django" theme). Subclasses may
        # override __init__/on_mount to register additional Textual themes —
        # no new public admin_tui name (Constitution V/VI).
        from admin_tui.themes import register_bundled_themes, resolve_theme_name

        register_bundled_themes(self)
        self.theme = resolve_theme_name(session)

    def on_mount(self) -> None:
        # Lazy import — screens land in Phase 3 (T049/T050).
        from admin_tui.screens.index import IndexScreen

        self.push_screen(IndexScreen(self.session))

    def action_show_help(self) -> None:
        self.notify(
            "Press q to quit. Arrow keys + Enter to navigate. "
            "See docs/quickstart.md for the full keymap.",
            title="admin_tui",
        )

    # --- screen-routing helpers (consulted by IndexScreen / Changelist).
    #
    # These exist so that defaults travel the extension path (Constitution
    # IV): overlays' `get_changelist_screen` / `get_detail_screen` always
    # decide which Screen class is instantiated.

    def screen_for_changelist(self, overlay, request):  # type: ignore[no-untyped-def]
        return overlay.get_changelist_screen(request)

    def screen_for_detail(self, overlay, request, obj=None):  # type: ignore[no-untyped-def]
        return overlay.get_detail_screen(request, obj)
