# Architecture

> **For the spec, the principles, and the contracts** see
> `specs/001-admin-tui-mvp/` and `.specify/memory/constitution.md`. This
> document is a single-page mental model for new contributors.

## The one-screen object graph

```text
                       AdminTuiApp (Textual App)
                              │
                              ├─ session : TuiSession
                              ▼
                    IndexScreen (apps → models)
                              │
                  ┌───────────┴───────────┐
                  ▼                       ▼
       ChangelistScreen           [tool screens registered
       (DataTable + actions)       via tui_site.register_screen]
                  │
                  ├─ Space toggles select
                  ├─ x  → _ActionPickerModal → ActionConfirmScreen
                  ├─ /  → _SearchModal
                  ├─ a  → ChangeScreen(mode="add")
                  └─ Enter → ChangeScreen(mode="view")
                                     │
                                     └─ e → ChangeScreen(mode="edit")
```

Every box on the right reads from **one TuiAdmin overlay**, which the
`TuiSite` (`admin_tui.tui_site`) maps to from the model. If no overlay
is registered, `TuiSite.get_or_synthesize(model)` returns a default
`TuiAdmin(model_admin)` — the same class user-written overlays subclass
(Constitution IV).

Permissions, form construction, validation, audit, search, filter, sort,
paginate — none of it lives in this package. Every one of those calls
through to a `ModelAdmin` method enumerated in
`specs/001-admin-tui-mvp/contracts/internal-django-surface.md`
(Constitution I).

## The synthetic request — the only tricky part

Even in-process, `ModelAdmin.get_changelist_instance(...)`, every
`has_*_permission(...)` call, and every action need a real `HttpRequest`
carrying the chosen user **and** a `_messages` backend (because
`message_user` defers to Django's messages framework).

`admin_tui/core/request.py::build_request(user, query=None)` synthesises
one:

- `django.test.RequestFactory().get(path, data=query)` — a real
  `HttpRequest`.
- `request.user = user`.
- `request._messages = _CapturingMessageStorage(request)` — a
  `BaseStorage` subclass that records every `(level, message, tags)`
  tuple to `request._messages.captured` and never touches cookies or
  sessions.
- `request._tui_session` — set to the live `TuiSession` by the CLI.

The capturing storage is what lets the `ActionConfirmScreen` surface
each `message_user(...)` call as a Textual `notify(...)`.

## Public surface freeze

Only these five names are public (`FR-030`, Constitution V):

```python
from admin_tui import register, TuiAdmin, tui_site, field_widgets, AdminTuiApp
```

The freeze is enforced by `tests/unit/test_public_api.py`, which asserts
`set(admin_tui.__all__) == set(_PUBLIC_NAMES)`. Adding a name requires
the FR-031 paperwork (justification, test, docs).

## Audit fidelity

Every create, edit, delete, and action MUST produce a `LogEntry` whose
content matches what the web admin would write for the same inputs
(SC-004). We route through the admin's own helpers:

- `ModelAdmin.log_addition(...)` (or `log_change`, `log_deletions`).
- `ModelAdmin.construct_change_message(request, form, formsets, add)` —
  the same change-message payload the web admin stores.

`core/audit.py` is a thin pass-through with one compat shim: Django 6.0
renamed `log_deletion(obj, repr)` to `log_deletions(queryset)`; the
shim dispatches on `hasattr(model_admin, "log_deletions")`.

## v2 — presentation, interaction & theming

The v2 redesign (`specs/002-ui-redesign-django-parity/`) is presentation +
interaction over the same data paths — it changes no admin behavior.

- **Stable changelist layout** (`widgets/layout.py`): `compute_column_widths`
  computes fixed, selection-independent column widths from the current page's
  rows (never the full queryset), and `truncate_cell` pre-truncates each cell
  (display-width aware). This replaces v1's content-auto-sizing + cursor
  auto-scroll — the cause of the "cropped columns / full text on select" glitch.
  Overflow is handled by intentional horizontal scrolling. The focused row's
  full values are shown in a fixed footer bar (no reflow).
- **Filter sidebar** (`widgets/filters.py`): renders Django's own
  `ChangeList.get_filters(request)` choices and applies their `query_string`
  verbatim — no filter logic is re-derived (Constitution I).
- **Mouse**: single click focuses, clicking the focused row / Enter opens, a
  checkbox-column click multi-selects, a header click sorts. All additive to the
  keyboard bindings; distinguished from Enter via the mouse-down column.
- **Theming** (`themes/`): a bundled `django` `textual.theme.Theme` (the admin
  palette) is the default; `ADMIN_TUI["THEME_NAME"]` selects a registered theme
  and the existing `ADMIN_TUI["THEME"]` `.tcss` is layered on top. No new public
  Python name — custom themes are registered by overriding `AdminTuiApp`.
- **Edit fix**: many-to-many fields now use a `SelectionList` (`widgets/
  defaults/many_to_many.py`) and the save path gathers list values; nullable
  FK/choice fields no longer crash the form. See `screens/change.py`.

## Where to look next

- `specs/001-admin-tui-mvp/contracts/public-api.md` — the documented
  hook signatures on `TuiAdmin`.
- `specs/001-admin-tui-mvp/contracts/cli.md` — `manage.py admin_tui`
  flags + exit codes.
- `specs/001-admin-tui-mvp/contracts/settings.md` — the `ADMIN_TUI`
  dict schema.
- `specs/001-admin-tui-mvp/contracts/internal-django-surface.md` — every
  Django admin call we depend on (Constitution I in code).
- `sample_project/library/tui.py` — the canonical overlay example.
