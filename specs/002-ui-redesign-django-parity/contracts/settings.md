# Contract: `ADMIN_TUI` Django settings dict (v2 delta)

v2 adds **one** key, `THEME_NAME`, to the single `ADMIN_TUI` namespace (FR-027 — one dict
keeps the public surface small). This supersedes v1's `contracts/settings.md` only by
appending `THEME_NAME`; all other keys are unchanged. Adding this key follows FR-031
(justification below + test + docs).

---

## Shape

```python
ADMIN_TUI = {
    "APP_CLASS": "admin_tui.app.AdminTuiApp",   # dotted import path
    "PAGE_SIZE": 50,                            # default changelist page size
    "THEME_NAME": None,                         # str | None — bundled/registered theme name  (NEW in v2)
    "THEME": None,                              # str | Path | None — .tcss override, layered on top
    "AUTODISCOVER": True,                       # whether to autodiscover `tui.py`
    "COMPAT_WARNINGS": True,                    # surface R16 compat report
}
```

Every key is optional; defaults apply when absent. Unknown keys raise `ImproperlyConfigured`
at `AppConfig.ready()` (unchanged).

---

## Per-key contract (changed / new rows)

| Key | Type | Default | Validation | Effect |
|-----|------|---------|------------|--------|
| `THEME_NAME` | `str` / `None` | `None` → resolves to `"django"` | Must name a theme registered at launch (the bundled `"django"`, the neutral fallback, or a Textual built-in / user-registered theme). Unknown name → `ImproperlyConfigured` (FR-018). Overridable per-invocation by `--theme-name`. | Sets `App.theme`. Selects the color palette. |
| `THEME` | str / `Path` / `None` | `None` | Existing: must be an existing readable `.tcss` file. Overridable by `--theme`. | Passed as `CSS_PATH`, **layered over** the selected theme; rules here override theme variables where they overlap (FR-015a). |

(Other keys — `APP_CLASS`, `PAGE_SIZE`, `AUTODISCOVER`, `COMPAT_WARNINGS` — unchanged from
v1.)

### Precedence (FR-015a)

1. `THEME_NAME` selects the palette (a `textual.theme.Theme`). Absent → `"django"`.
2. `THEME` (`.tcss`), if set, is layered on top and **wins** wherever it defines a rule
   that the theme also affects. A custom theme file alone is sufficient (it may ignore the
   palette entirely).
3. CLI flags (`--theme-name`, `--theme`) override the loaded values on the `TuiSession`
   only; they do not mutate the frozen config dict (unchanged reading-order rule).

---

## Bundled theme names

| Name | Description |
|------|-------------|
| `django` | **Default.** Evokes the Django admin palette (header green/blue, link blue, neutral greys) mapped to Textual theme variables. The look with no appearance config. |
| `textual-dark` *(and other Textual built-ins)* | Neutral fallback(s); re-exposed by name rather than re-authored. |

A project may also `register_theme(...)` its own `Theme` in an `AdminTuiApp` subclass and
select it by name via `THEME_NAME` — that path uses only public Textual API (Constitution
VI), no new admin_tui public name.

---

## Justification for the new key (FR-031)

- **Why needed:** spec FR-015 (user-selected "named themes + override") requires choosing
  the look without editing package code; a single `.tcss` path cannot offer a *selectable*
  set and cannot ship a zero-config default look.
- **Test:** `tests/unit/test_appearance_conf.py` (validation + precedence) and
  `tests/integration/sample_project/test_theming.py` (default + switch + invalid →
  `ImproperlyConfigured`).
- **Docs:** this contract + `quickstart.md` §Theming.

## Stability

`THEME_NAME` joins the v1.0.0 contract under SemVer. Removing/renaming any key is MAJOR;
adding another follows FR-031.
