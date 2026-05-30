# Contract: Theming (bundled themes, custom themes, `.tcss` override)

Theming is expressed entirely in Textual's own theming language (Constitution VI, FR-017):
**`textual.theme.Theme` objects** for the color palette and **Textual CSS (`.tcss`)** for
rule-level overrides. v2 introduces no parallel theming abstraction and no new public
`admin_tui` Python name.

---

## Two layers

1. **Palette layer — named themes.** A `textual.theme.Theme` defines the color variables
   (`primary`, `secondary`, `accent`, `foreground`, `background`, `surface`, `panel`,
   `success`, `warning`, `error`, plus dark/light). Selected by name via
   `ADMIN_TUI["THEME_NAME"]` (default `"django"`).
2. **Rule layer — `.tcss` override.** `ADMIN_TUI["THEME"]` (existing) is loaded as
   `App.CSS_PATH` and layered on top. Rules here reference theme variables (`$primary`,
   `$surface`, …) and override anything where they overlap (FR-015a).

A project can use either layer alone or both together.

---

## Bundled themes (`admin_tui/themes/`, internal)

| Name | Intent |
|------|--------|
| `django` | Default. Maps the Django admin palette (header green/blue `#417690`/`#0C4B33`-family, link blue, neutral greys) onto Textual variables so all screens evoke the admin. |
| neutral fallback | A Textual built-in (e.g. `textual-dark`) re-exposed by name; no second palette authored. |

Bundled themes are registered on the `App` at startup via `register_theme(...)`; the
resolved `THEME_NAME` is assigned to `App.theme`.

---

## Registering a custom theme (public, via Textual)

A downstream project subclasses `AdminTuiApp` (already public, Constitution V) and registers
its own `Theme`, then selects it by name:

```python
# myproject/tui_app.py
from textual.theme import Theme
from admin_tui import AdminTuiApp

MY_THEME = Theme(name="acme", primary="#5A2A82", dark=True)  # ... full Theme

class AcmeTuiApp(AdminTuiApp):
    def on_register_themes(self) -> None:      # hook called during theme registration
        super().on_register_themes()
        self.register_theme(MY_THEME)
```

```python
# settings.py
ADMIN_TUI = {
    "APP_CLASS": "myproject.tui_app.AcmeTuiApp",
    "THEME_NAME": "acme",
}
```

This uses only the public `AdminTuiApp` subclass point and Textual's own `register_theme` /
`Theme` — no new `admin_tui` public surface (Constitution V/VI). `on_register_themes` is a
documented overridable hook on `AdminTuiApp`; it follows FR-031 if added to the public hook
list.

---

## Validation & errors

- Unknown `THEME_NAME` (not registered at launch) → `ImproperlyConfigured` naming the key
  (FR-018, SC-005); the TUI does not start.
- `THEME` path validation is unchanged from v1 (must be an existing `.tcss` file).

## Stability

The default theme name `"django"` and the two-layer model are part of the v2 contract.
Renaming the default theme or removing a layer is a MAJOR change.
