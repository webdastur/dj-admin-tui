# Contract: `ADMIN_TUI` Django settings dict

The single namespace for package-level configuration (FR-027). One dict keeps the
public surface small and the docs short.

---

## Shape

```python
ADMIN_TUI = {
    "APP_CLASS": "admin_tui.app.AdminTuiApp",   # dotted import path
    "PAGE_SIZE": 50,                            # default changelist page size
    "THEME": None,                              # str | Path | None — .tcss file
    "AUTODISCOVER": True,                       # whether to autodiscover `tui.py`
    "COMPAT_WARNINGS": True,                    # surface R16 compat report
}
```

Every key is optional; the defaults above are applied if a key is absent. Unknown
keys raise `ImproperlyConfigured` at `AppConfig.ready()` time so typos are loud.

---

## Per-key contract

| Key | Type | Default | Validation | Effect |
|-----|------|---------|------------|--------|
| `APP_CLASS` | str (dotted import path) | `"admin_tui.app.AdminTuiApp"` | Must import; must be a subclass of `AdminTuiApp`. Otherwise `ImproperlyConfigured`. | Selects the Textual App. Overridable per-invocation by `--app`. |
| `PAGE_SIZE` | int | `50` | Must be `1 ≤ PAGE_SIZE ≤ 10_000`. | Default changelist page size when a `ModelAdmin` does not declare `list_per_page`. |
| `THEME` | str / `Path` / `None` | `None` | Must point at an existing readable file with `.tcss` extension. Overridable by `--theme`. | Passed as `CSS_PATH` to the App on construction. |
| `AUTODISCOVER` | bool | `True` | — | When `False`, skip `autodiscover_modules("tui")`. Tests may flip this to load overlays manually. |
| `COMPAT_WARNINGS` | bool | `True` | — | When `False`, suppress the R16 one-time notify per model. The report dict is still populated and available on the session for tests. |

## Reading order

1. `AppConfig.ready()` reads `getattr(settings, "ADMIN_TUI", {})` once and freezes
   the result on `admin_tui.conf._loaded`.
2. CLI flags (`--app`, `--theme`) override the loaded values on the `TuiSession`
   only — they do not mutate the loaded config dict.
3. No code path reads `settings.ADMIN_TUI` after `ready()`. (This avoids the
   gotcha where tests mutate settings mid-run and see inconsistent state.)

## Stability

The keys above are the v1.0.0 contract. Adding a key follows FR-031
(justification + test + docs). Removing or renaming a key is a MAJOR version
change.
