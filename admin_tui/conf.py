"""ADMIN_TUI settings loader.

Reads `settings.ADMIN_TUI` once on `AppConfig.ready()`, applies defaults,
and raises `ImproperlyConfigured` on unknown keys or invalid values. The
loaded snapshot is frozen on `_loaded` — no code reads `settings.ADMIN_TUI`
after `ready()` (so tests mutating settings mid-run get a consistent view).

See contracts/settings.md for the per-key contract.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import import_string

# Defaults applied when ADMIN_TUI is empty or a key is missing.
_DEFAULTS: dict[str, Any] = {
    "APP_CLASS": "admin_tui.app.AdminTuiApp",
    "PAGE_SIZE": 50,
    "THEME": None,
    "AUTODISCOVER": True,
    "COMPAT_WARNINGS": True,
}

_VALID_KEYS = frozenset(_DEFAULTS)

#: Frozen loaded settings. Populated by `_load()` at `AppConfig.ready()` time.
#: Tests may call `_load()` explicitly to refresh after monkey-patching settings.
_loaded: dict[str, Any] = dict(_DEFAULTS)


def _load() -> dict[str, Any]:
    """Read ADMIN_TUI from settings, validate, and freeze on `_loaded`.

    Idempotent: safe to call multiple times. Returns the loaded dict.
    """
    raw = getattr(settings, "ADMIN_TUI", {}) or {}
    if not isinstance(raw, dict):
        raise ImproperlyConfigured(
            f"ADMIN_TUI must be a dict, got {type(raw).__name__}."
        )

    unknown = set(raw) - _VALID_KEYS
    if unknown:
        raise ImproperlyConfigured(
            f"Unknown ADMIN_TUI keys: {sorted(unknown)}. "
            f"Valid keys: {sorted(_VALID_KEYS)}."
        )

    merged = {**_DEFAULTS, **raw}

    # Per-key validation.
    page_size = merged["PAGE_SIZE"]
    if not isinstance(page_size, int) or not (1 <= page_size <= 10_000):
        raise ImproperlyConfigured(
            f"ADMIN_TUI['PAGE_SIZE'] must be an int in [1, 10000], "
            f"got {page_size!r}."
        )

    theme = merged["THEME"]
    if theme is not None:
        theme_path = Path(theme)
        if not theme_path.is_file():
            raise ImproperlyConfigured(
                f"ADMIN_TUI['THEME'] does not exist: {theme_path}"
            )
        if theme_path.suffix != ".tcss":
            raise ImproperlyConfigured(
                f"ADMIN_TUI['THEME'] must be a .tcss file, got {theme_path}"
            )
        merged["THEME"] = theme_path

    if not isinstance(merged["AUTODISCOVER"], bool):
        raise ImproperlyConfigured(
            f"ADMIN_TUI['AUTODISCOVER'] must be bool, "
            f"got {merged['AUTODISCOVER']!r}."
        )

    if not isinstance(merged["COMPAT_WARNINGS"], bool):
        raise ImproperlyConfigured(
            f"ADMIN_TUI['COMPAT_WARNINGS'] must be bool, "
            f"got {merged['COMPAT_WARNINGS']!r}."
        )

    # APP_CLASS subclass check happens lazily in `resolve_app_class()` to
    # avoid an import cycle with admin_tui.app at module-load time.

    _loaded.clear()
    _loaded.update(merged)
    return _loaded


def resolve_app_class() -> type:
    """Import and return the configured AdminTuiApp subclass.

    Performed lazily to break the admin_tui.conf → admin_tui.app import
    cycle at AppConfig.ready() time.
    """
    from admin_tui.app import AdminTuiApp  # local to break cycle

    cls = import_string(_loaded["APP_CLASS"])
    if not isinstance(cls, type) or not issubclass(cls, AdminTuiApp):
        raise ImproperlyConfigured(
            f"ADMIN_TUI['APP_CLASS'] ({_loaded['APP_CLASS']}) is not a "
            f"subclass of admin_tui.AdminTuiApp."
        )
    return cls
