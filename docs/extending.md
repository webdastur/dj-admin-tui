# Extending the TUI

A project with `ModelAdmin`s works in the terminal with **no extra code** — the
TUI synthesizes a default overlay from your admin. You add a `tui.py` only to
layer TUI-specific behaviour on top; it never re-declares anything already in
your `ModelAdmin` (`list_display`, `search_fields`, `list_filter`, fieldsets, …).

Discovery mirrors `admin.py`: put a `tui.py` in any installed app and it's
autodiscovered at startup.

## Registering an overlay

```python
# myapp/tui.py
from admin_tui import register, TuiAdmin
from myapp.models import Book

@register(Book)
class BookTui(TuiAdmin):
    # Optional TUI-only slots — everything below is additive.
    row_actions = ["mark_featured"]          # per-row action methods
    bulk_actions = ["archive_selected"]      # multi-select action methods
    key_bindings = [("f", "mark_featured", "Feature")]  # (key, method, label)
    field_widgets = {}                       # per-model field → widget overrides

    def mark_featured(self, request, obj):
        obj.featured = True
        obj.save(update_fields=["featured"])
```

`@register(Book, Author)` registers one overlay for several models. Registering
a model that has no `ModelAdmin` raises `ImproperlyConfigured` — the TUI only
surfaces admin-registered models.

## Hook methods

`TuiAdmin` delegates to `self.model_admin` by default; override only what you
need. `self.model_admin` is public to read (don't mutate it).

```python
# Read paths
def get_list_columns(self, request) -> Sequence[str]: ...
def get_queryset(self, request) -> QuerySet: ...
def get_row_actions(self, request, obj) -> list[str]: ...
def get_bulk_actions(self, request) -> list[str]: ...

# Rendering — return Textual primitives, never wrapped
def render_cell(self, request, obj, field) -> BoundCellValue: ...
def get_changelist_screen(self, request) -> type[textual.screen.Screen]: ...
def get_detail_screen(self, request, obj=None) -> type[textual.screen.Screen]: ...

# Lifecycle
def before_save(self, request, obj, *, created: bool) -> None: ...
def after_save(self, request, obj, *, created: bool) -> None: ...
def before_action(self, request, action, queryset) -> None: ...
def after_action(self, request, action, queryset, *, result=None) -> None: ...

# Permission delegation — overlays should NOT override these
def has_view_permission(self, request, obj=None) -> bool: ...
def has_add_permission(self, request) -> bool: ...
def has_change_permission(self, request, obj=None) -> bool: ...
def has_delete_permission(self, request, obj=None) -> bool: ...
```

### Custom screens

To replace the changelist or detail view wholesale, return your own Textual
`Screen` subclass from `get_changelist_screen` / `get_detail_screen`. You're
handed Textual primitives directly — there's no wrapper layer to learn.

```python
def get_changelist_screen(self, request):
    from myapp.screens import BookBoard
    return BookBoard
```

## Custom field widgets

The field-widget registry maps **form-field classes** to Textual widget
factories. It walks the field's MRO, so a subclass of a registered field type
inherits its widget automatically. Register globally on `field_widgets`, or
per-model via the overlay's `field_widgets` slot.

```python
# myapp/tui.py
from admin_tui import field_widgets
from textual.widgets import Input
from myapp.forms_fields import ColorFormField

@field_widgets.register(ColorFormField)
def color_widget(bound_field):
    return Input(value=bound_field.value() or "", placeholder="#rrggbb")
```

A factory receives a Django `BoundField` and returns a Textual `Widget`. The
defaults cover text, boolean, choice, foreign key, many-to-many, date/datetime,
JSON, and numeric fields.

## Tool screens

Register a standalone screen not tied to a model:

```python
from admin_tui import tui_site
from myapp.screens import LogEntryScreen

tui_site.register_screen("logs", LogEntryScreen)
```

It appears in the index's tools picker (`g`).

## Theming

See [theming.md](./theming.md) — register a `textual.theme.Theme` by subclassing
`AdminTuiApp` and selecting it with `ADMIN_TUI["THEME_NAME"]`.
