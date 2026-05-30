# Quickstart: Django Admin TUI — v1

**Audience**: a Django developer with an existing project that already uses
`django.contrib.admin`. By the end of this page they have launched the TUI,
extended one model, and run a TUI-native action.

This file is the **operator-facing** quickstart. The detailed architecture lives
in `docs/architecture.md`; the public API lives in
[`contracts/public-api.md`](./contracts/public-api.md).

---

## 0. Trust model (read first)

The TUI runs **in-process** as a `manage.py` subcommand. There is no network
port, no token, no remote API.

> Whoever can run `manage.py` on the host already has full database access. The
> `--user` flag scopes which records the operator sees and attributes audit
> entries to that account — it is **NOT** an access-control boundary. Access
> control is the host's responsibility (Unix permissions, SSH, etc.).

If you need a remote, multi-operator TUI, that is a future opt-in mode
(Constitution VII); v1 does not provide it.

---

## 1. Install

```bash
# from PyPI (name TBD; the import name is admin_tui regardless)
uv add django-admin-tui            # or: pip install django-admin-tui

# in settings.py
INSTALLED_APPS += ["admin_tui"]
```

That's it. The package autodiscovers any `tui.py` module under each installed
app — same pattern as `admin.py`.

**Versions**: requires Python ≥ 3.12 and one of Django 4.2 LTS, 5.2 LTS, or 6.0.
Textual is pinned in our `pyproject.toml`; do not pin it yourself.

---

## 2. Launch

From the project root, with the venv active:

```bash
python manage.py admin_tui                # runs as the single superuser
python manage.py admin_tui --user alice   # runs as alice (must be is_staff)
```

You'll see an **index** of every app and model the web admin would show that
user. Arrows + Enter to drill in. `q` quits. `?` opens the keymap.

**What if I have a `ModelAdmin` but no `tui.py`?** The TUI works fully — that's
the zero-config promise (FR-021). You only write a `tui.py` to add TUI-specific
behavior.

---

## 3. Browse, edit, act (the operator's day-to-day)

The default screens mirror the web admin:

| You want to… | Press |
|--------------|-------|
| Open a model | Enter on the index row |
| Search | `/` |
| Open a filter sidebar | `f` |
| Sort by the current column | `s` (cycles asc → desc → unsorted) |
| Page through results | PgUp / PgDn |
| Open a record | Enter on a row |
| Add a new record | `a` |
| Edit | `e` (only if you have change permission) |
| Multi-select | Space |
| Run an action on the selection | `x` |
| Quit | `q` |

Saving uses the admin's `ModelForm`, so validation errors are exactly what the
web admin would show. Saves write an audit `LogEntry` attributed to the
`--user` (FR-008).

---

## 4. Extend the TUI for one of your models

Create `yourapp/tui.py` next to its `admin.py`. The package autodiscovers it.

```python
# yourapp/tui.py
from admin_tui import register, TuiAdmin
from .models import Book


@register(Book)
class BookTui(TuiAdmin):
    # TUI-native row action — appears in the row actions menu
    row_actions = ["mark_featured"]

    # Optional key binding — same shape as Textual's BINDINGS
    key_bindings = [("f", "mark_featured", "Feature")]

    # Per-cell render override — return any string (rich markup supported)
    def render_cell(self, request, obj, field):
        if field == "title" and obj.featured:
            return self.cell(display=f"[bold yellow]{obj.title}[/]")
        return super().render_cell(request, obj, field)

    # The action itself — runs against one row
    def mark_featured(self, request, obj):
        if not self.has_change_permission(request, obj):
            return
        obj.featured = True
        obj.save(update_fields=["featured"])
        self.model_admin.log_change(request, obj, "Marked featured via TUI")
```

You do **not** need to repeat any of the `ModelAdmin` config (list_display,
search_fields, filters, fieldsets, actions): the overlay inherits all of it from
the registered `ModelAdmin`. You only declare what's *new* for the TUI.

---

## 5. Register a custom field widget

```python
# yourapp/tui.py (continued)
from admin_tui import field_widgets
from .fields import ColorField
from .tui_widgets import ColorPickerWidget

@field_widgets.register(ColorField)
def _color_widget(bound_field):
    return ColorPickerWidget(value=bound_field.value())
```

`ColorPickerWidget` is a plain Textual `Widget` — we don't introduce a
parallel widget class (Constitution VI).

---

## 6. Replace a whole screen

When per-cell rendering or row actions aren't enough, return a `Screen` subclass:

```python
from textual.screen import Screen
from .my_screens import BookDashboard

class BookTui(TuiAdmin):
    def get_changelist_screen(self, request):
        return BookDashboard       # any Textual Screen subclass
```

You get full control: `BookDashboard.compose()` is Textual, not us.

---

## 7. Theme it

`.tcss` is Textual CSS:

```python
# settings.py
ADMIN_TUI = {
    "THEME": BASE_DIR / "tui_theme.tcss",
}
```

```css
/* tui_theme.tcss */
ChangelistScreen #table {
    background: $primary;
}
```

You can override per-launch with `--theme path/to/theme.tcss`.

---

## 8. Reskin the whole app

```python
# myproject/tui_app.py
from admin_tui import AdminTuiApp

class MyAdminTuiApp(AdminTuiApp):
    CSS_PATH = "tui_theme.tcss"

    BINDINGS = AdminTuiApp.BINDINGS + [
        ("g", "go_to_logs", "Logs"),
    ]

    def action_go_to_logs(self):
        self.push_screen("logs")     # a screen you registered on tui_site
```

```python
# settings.py
ADMIN_TUI["APP_CLASS"] = "myproject.tui_app.MyAdminTuiApp"
# or per-invocation: --app myproject.tui_app.MyAdminTuiApp
```

---

## 9. What's NOT supported in v1 (so you don't burn an hour)

- A network / remote mode. Run via SSH — that's the supported path.
- `ModelAdmin.change_view`, `ModelAdmin.get_urls`, admin JS, admin custom
  templates. These don't translate to the terminal. The TUI surfaces a one-time
  warning on first access to a model that declares any of them, listing what
  it skipped. Reproduce the behaviour with an overlay (`get_detail_screen`,
  `row_actions`, etc.).
- Models not registered with `django.contrib.admin`. The TUI mirrors the admin
  registry exactly.

---

## 10. Verify your install (sample-app smoke test)

```bash
# from the repo root, after a dev install (`uv sync`)
uv run pytest tests/integration/sample_project -q
```

Every test exercises the public API: registration, the widget registry, a
TUI-native action, and permission scoping. If they all pass, your install is
sound. If you've added an overlay in your own project and want a quick check,
launch the TUI as a non-superuser and confirm: only the models that user can
see appear in the index, the row actions you declared show up, and an edit
writes a `LogEntry` (`Site administration → log entries` in the web admin).

---

## Where to go next

- **Public API reference**: [`contracts/public-api.md`](./contracts/public-api.md)
- **CLI flags and exit codes**: [`contracts/cli.md`](./contracts/cli.md)
- **`ADMIN_TUI` settings**: [`contracts/settings.md`](./contracts/settings.md)
- **The principles that bind the design**: [`/.specify/memory/constitution.md`](../../.specify/memory/constitution.md)
- **The full feature spec**: [`spec.md`](./spec.md)
