# Public API

The entire top-level public surface is five names. Everything else under
`admin_tui.*` is internal and may change without notice.

```python
from admin_tui import (
    register,        # decorator/function — register a TuiAdmin for a model
    TuiAdmin,        # base class for per-model overlays
    tui_site,        # the default TuiSite singleton
    field_widgets,   # the default FieldWidgetRegistry singleton
    AdminTuiApp,     # the Textual App subclass; user code may subclass
)
```

A regression test asserts `admin_tui.__all__` equals this list exactly.

## `register`

```python
def register(*models, site=tui_site) -> Callable[[type[TuiAdmin]], type[TuiAdmin]]:
    ...
```

Class decorator that registers a `TuiAdmin` overlay for one or more models.
Raises `AlreadyRegistered` if a model is already registered, and
`ImproperlyConfigured` if the model has no `ModelAdmin`.

## `TuiAdmin`

Base class for per-model overlays. Declarative slots:

```python
list_columns: Sequence[str] | None = None
detail_fieldsets: Sequence[Any] | None = None
row_actions: list[str] = []
bulk_actions: list[str] = []
key_bindings: list[tuple[str, str, str]] = []   # (key, method, label)
field_widgets: dict[type[models.Field], Callable] = {}
```

Plus the hook methods documented in [extending.md](./extending.md). All hooks
default to delegating to the public `self.model_admin`.

## `tui_site`

The process-wide registry singleton. Public operations:

```python
tui_site.register(model, overlay=None) -> None
tui_site.unregister(model) -> None
tui_site.register_screen(slug, screen_cls) -> None
tui_site.is_registered(model) -> bool
```

The `TuiSite` class itself is internal; instantiate-your-own-site is not part of
the v1 surface.

## `field_widgets`

The default field-widget registry. Public operations:

```python
field_widgets.register(field_cls, factory) -> Callable   # usable as a decorator
field_widgets.is_registered(field_cls) -> bool
```

## `AdminTuiApp`

The Textual application; subclass to reskin or extend wholesale. Selected via
`ADMIN_TUI["APP_CLASS"]` or `--app`.

```python
class AdminTuiApp(textual.app.App):
    def __init__(self, *, session) -> None: ...
```

Subclass contract:
- MAY add screens, `BINDINGS`, CSS, and register Textual themes.
- MUST call `super().__init__(session=session)` if overriding `__init__`.
- MUST NOT override the internal screen-routing methods that consult
  `TuiAdmin.get_*_screen(...)` — those are how overlays customise views.

## Stability (SemVer)

- **MAJOR** — remove a public name; change a public signature incompatibly;
  remove a `TuiAdmin` hook.
- **MINOR** — add a public name; add a hook; add an optional keyword argument.
- **PATCH** — bug fix; doc fix; internal refactor preserving every signature.

Deprecations keep the old shape with a `DeprecationWarning` for at least two
minor versions (or one year), then remove it only in the next major.
