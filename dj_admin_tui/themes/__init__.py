"""Bundled Textual themes + appearance resolution.

Two-layer theming (see docs/theming.md):
  1. a named ``textual.theme.Theme`` selected by ``ADMIN_TUI["THEME_NAME"]``
     (the palette layer), defaulting to the bundled ``django`` theme;
  2. the existing ``ADMIN_TUI["THEME"]`` ``.tcss`` override layered on top.

Internal module — no public ``dj_admin_tui`` name is added; downstream projects
register their own themes by overriding the public ``AdminTuiApp``, and select
them via ``THEME_NAME``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from dj_admin_tui.themes.django import DJANGO_DARK_THEME, DJANGO_THEME

if TYPE_CHECKING:
    from dj_admin_tui._internal.session import TuiSession
    from dj_admin_tui.app import AdminTuiApp

#: Default theme name applied when ``THEME_NAME`` is unset — the Django admin
#: **dark** palette (high-contrast dark mode is the default look).
DEFAULT_THEME_NAME = "django-dark"
#: A neutral fallback (a Textual built-in, re-exposed by name).
NEUTRAL_THEME_NAME = "textual-dark"

#: Themes this package ships, by name (dark default + the light admin palette).
BUNDLED_THEMES = {
    DJANGO_DARK_THEME.name: DJANGO_DARK_THEME,
    DJANGO_THEME.name: DJANGO_THEME,
}


def register_bundled_themes(app: AdminTuiApp) -> None:
    """Register every bundled theme on the App (idempotent per App)."""
    for theme in BUNDLED_THEMES.values():
        app.register_theme(theme)


def valid_theme_names() -> set[str]:
    """Names accepted for ``THEME_NAME``: bundled themes + Textual built-ins."""
    from textual.theme import BUILTIN_THEMES

    return set(BUNDLED_THEMES) | set(BUILTIN_THEMES)


def resolve_theme_name(session: TuiSession) -> str:
    """The theme name to apply for a session (its ``theme_name`` or the default)."""
    return getattr(session, "theme_name", None) or DEFAULT_THEME_NAME
