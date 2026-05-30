# Data Model: Django Admin TUI — v1

**Branch**: `001-admin-tui-mvp` | **Date**: 2026-05-30

The TUI introduces **no persistent storage**. The data model below describes the
in-process objects that flow between the CLI entry point, the screens, and the
Django admin. Persisted data is whatever the host project stores; the TUI only
records audit via Django's `LogEntry` (via existing admin helpers — we never
write rows directly).

---

## 1. `TuiSession` (in-memory, per-run)

**What**: the single context object that represents one run of `manage.py admin_tui`.
Created by the management command after `--user` is resolved, attached to every
synthetic request as `request._tui_session`, and accessible to overlays via the
`request` they receive in hook methods.

**Fields**:

| Field | Type | Source | Description |
|------|------|--------|-------------|
| `user` | `django.contrib.auth.get_user_model()` instance | resolved from `--user` or default superuser | The Django user whose permissions and audit attribution drive the session. Must be `is_staff=True`. |
| `started_at` | `datetime` (aware, project timezone) | `now()` at command entry | For audit context only; never written anywhere. |
| `messages_log` | `list[tuple[int, str, str]]` | accumulated from every `_CapturingMessageStorage` flush | A flat record of every `message_user` call across the session. Surfaced in the "messages" overlay screen. |
| `compat_report` | `dict[Model, list[str]]` | populated once at startup by `_internal.compat.scan(admin.site)` | The "custom ModelAdmin overrides we won't honour" detection (R16). |
| `app_class` | `type[AdminTuiApp]` | from settings or `--app` flag | Allows downstream projects to subclass the App. |
| `theme_path` | `pathlib.Path \| None` | `ADMIN_TUI["THEME"]` | `.tcss` path applied via `App.CSS_PATH`. |

**Lifecycle**: created on command start, destroyed on App exit. Single instance;
NOT a Django model.

**Validation**:
- `user.is_active` MUST be `True` (FR-003).
- `user.is_staff` MUST be `True` (FR-003).
- If `user` is `None`, the command resolves a default superuser; if more than one
  superuser exists and `--user` is unset, the command exits with a clear error
  asking for `--user` (FR-002).

---

## 2. `TuiSite` (process-wide registry)

**What**: the parallel-to-`admin.site` registry that maps Django models to their
TUI overlay. Provides the public `register()` decorator and the `tui_site`
singleton.

**Fields**:

| Field | Type | Description |
|------|------|-------------|
| `_registry` | `dict[Model, TuiAdmin]` | the actual map. Populated by autodiscovery (R10) and by `_synthesize` on first access. |
| `_screens` | `dict[str, type[Screen]]` | global tool screens (≈ admin `get_urls` extension point). |
| `_synth_cache` | `dict[ModelAdmin, TuiAdmin]` | so re-synthesising for the same `ModelAdmin` returns the same instance (identity stability matters for overlay equality checks in tests). |

**Operations** (every operation is public unless prefixed `_`):

| Operation | Signature | Behaviour |
|-----------|-----------|-----------|
| `register` | `(model, tui_admin_cls=None)` (also usable as decorator) | wraps `tui_admin_cls(model_admin)` and adds to `_registry`. Raises `AlreadyRegistered` if already present. |
| `register_screen` | `(slug, screen_cls)` | adds to `_screens`. Slugs collide → raise. |
| `get_or_synthesize` | `(model)` | returns the registered overlay; if none, looks up the `ModelAdmin` from `admin.site._registry[model]` and synthesises a default `TuiAdmin(model_admin)`, caches, and returns. |
| `models_for` | `(request)` | returns `[(app_label, model, overlay), ...]` filtered by `has_module_permission` + `has_view_permission` for the session user. Used by the index screen. |

**Invariants**:
- A model NOT registered with `admin.site` is NEVER in `_registry` and NEVER
  appears in `models_for(...)` output. (Spec Assumptions.)
- An overlay's `model_admin` attribute MUST point at the live
  `admin.site._registry[model]`. If the host project unregisters or replaces a
  `ModelAdmin` mid-run, the next call to `get_or_synthesize` returns a fresh
  overlay. (Edge case: extremely rare in practice; covered for fidelity.)

---

## 3. `TuiAdmin` (per-model overlay)

**What**: the public extension base class. Every model the TUI shows is backed by
exactly one `TuiAdmin` instance (synthesised default or developer-written).

**Constructor**: `TuiAdmin(model_admin)` — store the source `ModelAdmin` so
declarative slots can fall through to it. NEVER store data the `ModelAdmin`
already carries.

**Declarative slots** (each defaults to delegating to `self.model_admin`):

| Slot | Type | Default | Notes |
|------|------|---------|-------|
| `list_columns` | `Sequence[str] \| None` | `None` → falls through to `model_admin.get_list_display(request)` | TUI-specific override of changelist columns. |
| `detail_fieldsets` | fieldsets tuple or `None` | `None` → `model_admin.get_fieldsets(request, obj)` | |
| `row_actions` | `list[str]` | `[]` | Names of TUI-native per-row actions (method names on this class). |
| `bulk_actions` | `list[str]` | `[]` | Names of TUI-native bulk actions. |
| `key_bindings` | `list[tuple[str, str, str]]` | `[]` | `(key, action_method_name, description)`. Forwarded to the active Screen's `BINDINGS`. |
| `field_widgets` | `dict[type[models.Field], Callable]` | `{}` | Per-overlay widget overrides; merged on top of the global `field_widgets` registry. |

**Request-aware hooks** (each is a default no-op or a delegate to `model_admin`):

| Hook | Signature | Default |
|------|-----------|---------|
| `get_list_columns` | `(request)` | reads `list_columns` or `model_admin.get_list_display(request)` |
| `get_queryset` | `(request)` | `model_admin.get_queryset(request)` |
| `get_row_actions` | `(request, obj)` | filters `row_actions` by per-action permission check |
| `get_bulk_actions` | `(request)` | filters `bulk_actions` by permission |
| `render_cell` | `(request, obj, field)` | calls `ModelAdmin.lookup_allowed(field)` and renders via the field's widget. Overridable. |
| `get_changelist_screen` | `(request)` | returns `screens.changelist.ChangelistScreen`. Override returns a custom `Screen` subclass. |
| `get_detail_screen` | `(request, obj=None)` | returns `screens.change.ChangeScreen`. Override returns a custom `Screen` subclass. |
| `before_save` / `after_save` | `(request, obj, created)` | no-op |
| `before_action` / `after_action` | `(request, action, queryset, result=None)` | no-op |

**Permission delegation**: `has_view_permission(request, obj=None)`, etc., return
`self.model_admin.has_view_permission(request, obj)`. We never override these.

**State transitions** for an object viewed in the TUI:

```
        ┌──── view (changelist row) ───┐
        ▼                              │
  [index]──open──►[changelist]──open──►[detail (read)]
                       │                    │
                  add  │              edit  │
                       ▼                    ▼
                   [detail (create)]   [detail (edit)]
                       │                    │
                  save │              save  │
                       ▼                    ▼
                   ┌── after_save fires; log_addition / log_change written ──┐
                       │                                                     │
                       ▼                                                     ▼
                  back to [changelist]                              back to [changelist]

  multi-select on [changelist] ──► [action_confirm] ──run──► after_action fires,
                                                              log_deletion if delete
```

Permission gates at every arrow: open → `has_view_permission`; add →
`has_add_permission`; edit → `has_change_permission`; delete (in actions or as a
selected action) → `has_delete_permission`; running a `ModelAdmin`-declared
action → already filtered by `get_actions(request)`; running a TUI-native row /
bulk action → `TuiAdmin.has_change_permission(...)` unless the action overrides.

---

## 4. `FieldWidgetRegistry` (process-wide)

**What**: maps model field classes to factory callables that produce Textual
widgets, with MRO walking and per-overlay overrides.

**Fields**:

| Field | Type | Description |
|------|------|-------------|
| `_table` | `dict[type[models.Field], Callable[[BoundField], Widget]]` | The explicit registrations. |
| `_resolved_cache` | `dict[type[models.Field], Callable]` | Memoised MRO walk results. |

**Operations**:

| Operation | Signature | Behaviour |
|-----------|-----------|-----------|
| `register` | `(field_cls, factory)` (also as decorator) | adds to `_table`; invalidates `_resolved_cache`. |
| `resolve` | `(bound_field, overlay=None)` → factory | (1) if `overlay.field_widgets` has the exact field class, return it. (2) else walk `type(bound_field.field).__mro__` against `_table`. (3) else fall through to a default text-input widget. The first hit wins and is cached. |

**MRO walk** matters because user code commonly subclasses Django fields
(`class JSONField(models.JSONField): ...`) and expects subclasses to inherit the
parent's widget without re-registration — explicit in FR-025.

---

## 5. `BoundCellValue` (transient, returned by `render_cell`)

**What**: a minimal value object the changelist's `DataTable` consumes.

| Field | Type | Description |
|------|------|-------------|
| `display` | `str` | the text/rich-markup the cell shows (passes through Textual's escaping). |
| `sort_key` | `Any` | the value the column sorts by (defaults to `display`). |
| `style` | `str \| None` | optional Textual style string (e.g. `"bold red"`); the column renderer is free to ignore. |

**Validation**: `display` MUST be a string; non-string values from a user
`render_cell` are coerced with `str(...)` after a one-time warning per overlay.

---

## 6. `AuditRecord` (handle, not a model)

**What**: thin pass-through type to keep call sites readable.

```python
@dataclass(frozen=True)
class _AuditRecord:
    log_type: Literal["add", "change", "delete"]
    user_id: int
    content_type_id: int
    object_id: str
    object_repr: str
    change_message: list[dict[str, Any]] | str
```

We construct one only to pass into `model_admin.log_*` helpers (so callers don't
need to remember the helper signatures); it is never persisted directly.

---

## Relationships (object graph)

```
TuiSession ────────► User (Django auth model)
   │
   ├──► AdminTuiApp ───► IndexScreen ──► ChangelistScreen ──► ChangeScreen
   │                          │                    │
   │                          └─ uses ─►  TuiSite ─┴─► TuiAdmin ──► ModelAdmin (Django)
   │                                          │
   │                                          └─► FieldWidgetRegistry
   │
   └──► _CapturingMessageStorage (attached to every request as ._messages)
```

Every arrow is in-process; nothing crosses the wire.
