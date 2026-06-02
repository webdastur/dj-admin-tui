# Configuration

All package configuration lives under a single `ADMIN_TUI` dict in your Django
settings. Every key is optional; defaults apply when a key is absent. Unknown
keys raise `ImproperlyConfigured` at startup so typos are loud.

```python
# settings.py
ADMIN_TUI = {
    "APP_CLASS": "dj_admin_tui.app.AdminTuiApp",   # dotted import path
    "PAGE_SIZE": 50,                            # default changelist page size
    "THEME_NAME": None,                         # bundled/registered theme name
    "THEME": None,                              # path to a .tcss override
    "AUTODISCOVER": True,                        # discover `tui.py` modules
    "COMPAT_WARNINGS": False,                     # FYI when an admin mounts extra pages
}
```

## Keys

| Key | Type | Default | Effect |
|-----|------|---------|--------|
| `APP_CLASS` | dotted path | `dj_admin_tui.app.AdminTuiApp` | The Textual `App` subclass to launch. Must import and subclass `AdminTuiApp`. Overridable per launch with `--app`. |
| `PAGE_SIZE` | int (1–10000) | `50` | Default changelist page size when a `ModelAdmin` doesn't set `list_per_page`. |
| `THEME_NAME` | str / `None` | `None` → `"django-dark"` | Selects the colour theme (palette). Must name a registered theme. Overridable with `--theme-name`. See [theming.md](./theming.md). |
| `THEME` | path / `None` | `None` | A Textual `.tcss` file layered on top of the theme. Overridable with `--theme`. |
| `AUTODISCOVER` | bool | `True` | When `False`, skip autodiscovery of `tui.py` modules. |
| `COMPAT_WARNINGS` | bool | `False` | A registered `ModelAdmin` is driven in full with no overlay — forms, fieldsets, saves, and permissions all come from it, so its add/change/delete just work. When `True`, the TUI adds a one-time per-model heads-up if the admin mounts *extra* pages via a custom `get_urls` (e.g. a report or password-change view) that have no terminal equivalent. Off by default. |

## Reading order

1. At startup the package reads `ADMIN_TUI` once, validates it, and freezes the
   result. No code reads `settings.ADMIN_TUI` again, so tests that mutate
   settings mid-run see a consistent view.
2. CLI flags (`--app`, `--theme`, `--theme-name`) override the loaded values for
   that launch only; they don't mutate the frozen config.

## Stability

These keys are the v1.0 contract. Removing or renaming a key is a major version
change; adding a key is a minor version change. See [api.md](./api.md) for the
full stability policy.
