# Contract: Public Python API

**Source of truth for FR-030 (the public surface) and Constitution Principle V.**

This file fixes the names, signatures, and stability promises of every public
name `admin_tui` exposes at v1.0. A regression test
(`tests/unit/test_public_api.py`) reads this list from
`admin_tui/_internal/public_api.py::_PUBLIC_NAMES` and asserts
`admin_tui.__all__` matches exactly. Adding to this list requires the
justification + test + docs entry mandated by FR-031.

---

## The complete public surface

```python
from admin_tui import (
    register,         # decorator/function — register a TuiAdmin for a model
    TuiAdmin,         # base class for per-model overlays
    tui_site,         # the default TuiSite singleton
    field_widgets,    # the default FieldWidgetRegistry singleton
    AdminTuiApp,      # the Textual App subclass; user code may subclass
)
```

That's the entire top-level surface. Everything else — including `TuiSite`,
`FieldWidgetRegistry`, the screens, the synthetic-request helpers, and the
internal admin-bridging functions — is `_internal` and may change without
notice.

---

## 1. `register`

```python
def register(
    *models: type[django.db.models.Model],
    site: TuiSite = tui_site,
) -> Callable[[type[TuiAdmin]], type[TuiAdmin]]:
    """Class decorator that registers a TuiAdmin overlay for one or more models.

    Usage:
        @register(Book)
        class BookTui(TuiAdmin):
            ...

        @register(Book, Author, Tag)
        class SharedTui(TuiAdmin):
            ...
    """
```

**Errors**:
- `AlreadyRegistered` — at least one of `models` is already registered on `site`.
- `ImproperlyConfigured` — the model has no `ModelAdmin` registered with
  `django.contrib.admin.site`. (The TUI does not surface models that are not
  admin-registered — see Spec Assumptions.)

**Stability**: covered by SemVer. The decorator MAY accept additional keyword
arguments in future minor versions, but their absence MUST remain valid.

---

## 2. `TuiAdmin`

Every overlay subclasses `TuiAdmin`. The full slot + hook surface is documented
under [data-model.md §3](../data-model.md#3-tuiadmin-per-model-overlay). The
contract here is the **method signatures** — these MUST NOT change in a way that
breaks subclasses across minor versions.

### Declarative slots (class attributes, type-annotated)

```python
class TuiAdmin:
    list_columns: Sequence[str] | None = None
    detail_fieldsets: Sequence[Any] | None = None
    row_actions: list[str] = []
    bulk_actions: list[str] = []
    key_bindings: list[tuple[str, str, str]] = []
    field_widgets: dict[type[models.Field], Callable] = {}
```

### Hook methods (default to delegating to `self.model_admin`)

```python
def __init__(self, model_admin: admin.ModelAdmin) -> None: ...

# Read paths
def get_list_columns(self, request: HttpRequest) -> Sequence[str]: ...
def get_queryset(self, request: HttpRequest) -> QuerySet: ...
def get_row_actions(self, request: HttpRequest, obj) -> list[str]: ...
def get_bulk_actions(self, request: HttpRequest) -> list[str]: ...

# Rendering — Textual primitives, never wrapped
def render_cell(
    self,
    request: HttpRequest,
    obj,
    field: str,
) -> "BoundCellValue": ...

def get_changelist_screen(
    self, request: HttpRequest,
) -> type["textual.screen.Screen"]: ...

def get_detail_screen(
    self, request: HttpRequest, obj=None,
) -> type["textual.screen.Screen"]: ...

# Lifecycle
def before_save(self, request: HttpRequest, obj, *, created: bool) -> None: ...
def after_save(self, request: HttpRequest, obj, *, created: bool) -> None: ...
def before_action(self, request: HttpRequest, action: str, queryset) -> None: ...
def after_action(
    self, request: HttpRequest, action: str, queryset, *, result=None,
) -> None: ...

# Permission delegation — overlays SHOULD NOT override these
def has_view_permission(self, request, obj=None) -> bool: ...
def has_add_permission(self, request) -> bool: ...
def has_change_permission(self, request, obj=None) -> bool: ...
def has_delete_permission(self, request, obj=None) -> bool: ...
```

**The `model_admin` attribute is public**: overlays may read `self.model_admin`
to delegate, fall through, or inspect. They MUST NOT mutate it.

**`BoundCellValue`** is exposed under `admin_tui.values.BoundCellValue` — added
to the public surface at v1.0.1 if `render_cell` returns it; for v1.0.0 it is
re-exported via `admin_tui.TuiAdmin.cell` as a class attribute alias to keep the
top-level `__all__` at the documented six names. (See "Deferred public additions"
below.)

### Deprecation policy

A hook removal or signature change MUST follow:
1. The new shape is added in minor version N. The old shape is kept and emits a
   `DeprecationWarning` referencing this contract.
2. At least two minor versions pass, OR one full year, whichever is longer.
3. The old shape is removed only in the next MAJOR.

---

## 3. `tui_site`

```python
tui_site: TuiSite  # the process-wide default registry singleton
```

`TuiSite` itself is `admin_tui._internal.sites.TuiSite` — instantiating a
**custom site** is a `_PUBLIC_NAMES` addition we'll only make when a real user
need surfaces (Constitution V). For v1, `tui_site` is the only entry point.

Public operations on the singleton (signatures match [data-model.md §2](../data-model.md#2-tuisite-process-wide-registry)):

```python
tui_site.register(model: type[Model], overlay: type[TuiAdmin] | None = None) -> None
tui_site.unregister(model: type[Model]) -> None
tui_site.register_screen(slug: str, screen_cls: type["textual.screen.Screen"]) -> None
tui_site.is_registered(model: type[Model]) -> bool
```

**Stability**: every name above is part of the v1 contract. Additions MUST
follow FR-031 (justification + test + docs).

---

## 4. `field_widgets`

```python
field_widgets: FieldWidgetRegistry
```

Public operations:

```python
field_widgets.register(
    field_cls: type[models.Field],
    factory: Callable[[forms.BoundField], "textual.widget.Widget"],
) -> Callable  # may be used as decorator

field_widgets.is_registered(field_cls: type[models.Field]) -> bool
```

**`resolve(...)` is intentionally NOT public**: callers should not need to
short-circuit the registry's MRO walk. If a real need arises, it becomes a v1.x
addition with the standard justification.

---

## 5. `AdminTuiApp`

```python
class AdminTuiApp(textual.app.App):
    """The Textual application. Subclass to reskin or extend wholesale.

    Selected via `ADMIN_TUI["APP_CLASS"]` (dotted-path import) or `--app`.
    """

    CSS_PATH: ClassVar[str | Path | None]
    BINDINGS: ClassVar[list[tuple]]

    def __init__(self, *, session: "TuiSession") -> None: ...

    def on_mount(self) -> None: ...
    def compose(self) -> "textual.app.ComposeResult": ...
```

**Subclass contract**:
- Subclasses MAY add screens, BINDINGS, and CSS.
- Subclasses MUST call `super().__init__(session=session)` if they override
  `__init__`.
- Subclasses MUST NOT override the screen-routing methods that consult
  `TuiAdmin.get_*_screen(...)` — those are the only way overlays customise
  views, and bypassing them breaks Constitution IV.

---

## Deferred public additions (NOT in v1.0.0)

Things we considered exposing and rejected per Constitution V's "default no":

- `TuiSite` class (vs. only the singleton) — no user has asked for multiple
  sites. Defer.
- `FieldWidgetRegistry.resolve` — no use case beyond the framework itself.
- `BoundCellValue` as a top-level name — only `render_cell` overrides see it,
  and they get it via the `TuiAdmin.cell` helper. Promote when a non-overlay
  consumer surfaces.
- A `tui_widget` decorator on `field_widgets` parallel to `@register` — pure
  sugar; no behavioural delta. Defer.
- Direct exposure of `_CapturingMessageStorage` — overlay authors should never
  need to construct one; the synthetic request already carries one.

Each of these will be re-evaluated when a concrete consumer story exists, per
FR-031 (justification + test + docs).

---

## SemVer policy summary

- **MAJOR** — remove a public name; change a public signature
  incompatibly; remove a hook method from `TuiAdmin`.
- **MINOR** — add a public name (with FR-031 paperwork); add a hook method;
  add an optional kwarg to a public signature.
- **PATCH** — bugfix; doc fix; internal refactor that preserves every signature.

The constitution version is independent of the package version (Governance §
"Constitution versioning"); a bug-fix release of the package does not amend the
constitution and vice versa.
