# Theming

Theming is expressed entirely in Textual's own theming language — there is no
parallel abstraction. Two layers compose:

1. **Palette layer — a named `textual.theme.Theme`.** Selected with
   `ADMIN_TUI["THEME_NAME"]` (or `--theme-name`). Provides the colour variables
   (`primary`, `secondary`, `accent`, `foreground`, `background`, `surface`,
   `panel`, `success`, `warning`, `error`, …).
2. **Rule layer — a `.tcss` override.** `ADMIN_TUI["THEME"]` (or `--theme`) is
   loaded as `App.CSS_PATH` and layered on top. Rules here reference theme
   variables (`$primary`, `$surface`, …) and win wherever they overlap.

You can use either layer alone or both together.

## Bundled themes

| Name | Intent |
|------|--------|
| `django-dark` | **Default.** The Django admin's dark palette — dark surfaces with the admin's blue/teal accents. |
| `django` | The classic light Django admin palette. |
| Textual built-ins | `textual-dark`, `nord`, `gruvbox`, `dracula`, … re-exposed by name as neutral options. |

With no appearance configuration you get `django-dark`.

```python
# settings.py
ADMIN_TUI = {
    "THEME_NAME": "django",            # or "django-dark", "textual-dark", …
    "THEME": "/path/to/custom.tcss",   # optional, layered on top
}
```

Per launch: `python manage.py admin_tui --theme-name django`. An unknown theme
name fails fast with `ImproperlyConfigured` — no broken screen is shown.

## A custom `.tcss` override

A `.tcss` file alone is enough if you want full control. It references the
active theme's variables:

```css
/* myproject/admin_tui.tcss */
ChangelistScreen #filter-sidebar {
    border-left: solid $accent;
}
```

```python
ADMIN_TUI = {"THEME": "myproject/admin_tui.tcss"}
```

## Registering your own theme

Subclass `AdminTuiApp`, register a `textual.theme.Theme`, and select it by name.
This uses only the public `AdminTuiApp` subclass point and Textual's own
`register_theme` — no new `admin_tui` API:

```python
# myproject/tui_app.py
from textual.theme import Theme
from admin_tui import AdminTuiApp

ACME = Theme(name="acme", primary="#5A2A82", dark=True)  # … full Theme

class AcmeTuiApp(AdminTuiApp):
    def __init__(self, *, session):
        super().__init__(session=session)
        self.register_theme(ACME)
        self.theme = "acme"
```

```python
# settings.py
ADMIN_TUI = {"APP_CLASS": "myproject.tui_app.AcmeTuiApp"}
```

## Precedence

1. `THEME_NAME` selects the palette (default `django-dark`).
2. `THEME` (`.tcss`) is layered on top and overrides any rule it defines.
3. CLI flags override the settings values for that launch only.

Changing the theme never affects data behaviour — result sets, permissions,
saves, and audit are identical across themes.
