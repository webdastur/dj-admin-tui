# Architecture

A one-page tour of how the TUI is put together. The guiding rule: **reuse
Django's admin; never reimplement it.** All domain behaviour — querysets,
search, filtering, ordering, pagination, form construction, validation,
permissions, actions, and audit — is produced by the registered `ModelAdmin`
and Django's own internals. The TUI renders that output in the terminal.

## The synthetic request

The TUI runs in-process with no HTTP layer, but the admin API expects a
`request`. Each session builds one synthetic `HttpRequest` scoped to the chosen
user (a single choke point), carrying a message store that captures
`message_user(...)` output. Every admin call — `get_changelist_instance`,
`get_form`, `has_*_permission`, the action callables — receives this request, so
permissions and audit behave exactly as the web admin would for that user.

## Object graph

```
AdminTuiApp (Textual App)
  └── pushes Screens:
        IndexScreen       apps → models (permission-scoped)
        ChangelistScreen  DataTable + search + sort + filter sidebar + pagination
        ChangeScreen      detail / create / edit (admin fieldsets + widgets)
        ActionConfirmScreen  confirm + run admin actions / delete

TuiSite (registry)        model → TuiAdmin overlay
  └── synthesizes a default TuiAdmin from the ModelAdmin when none is registered

TuiAdmin (overlay)        per-model TUI behaviour; delegates to self.model_admin

FieldWidgetRegistry       form-field class → Textual widget factory (MRO walk)
```

Defaults travel the **same** path third-party extensions use: the default
overlay is a synthesized `TuiAdmin`, and screens are always chosen via
`overlay.get_*_screen(...)` — there is no privileged internal render path. (See
[extending.md](./extending.md).)

## Changelist layout & truncation

Textual's `DataTable` auto-sizes columns to content and auto-scrolls to the
cursor cell. To keep the list stable, the TUI computes **fixed,
selection-independent** column widths once per rebuild (sampling only the
current page, never the whole queryset) and **pre-truncates** each cell with an
ellipsis (display-width aware, so CJK/emoji don't break alignment). Overflow is
handled by intentional horizontal scrolling; the focused row's full values show
in a fixed footer bar. Widths recompute on search / filter / sort / page — never
on cursor movement.

Sorting and filtering defer to Django: the filter sidebar is built from
`ChangeList.get_filters(request)` and applies the admin's own query strings; the
sort arrows and which columns are sortable come from
`ChangeList.get_ordering_field_columns()` / `get_ordering_field(...)`, so
`ModelAdmin.ordering`, `sortable_by`, and `admin_order_field` all apply.

## Forms, save & audit

Create/edit forms come from `ModelAdmin.get_form(request, obj)`, so every
`clean_*` / `clean` validator runs unchanged. On save the TUI mirrors the
admin's change-form sequence — `save_model` → `save_related` →
`construct_change_message` → `log_addition` / `log_change` — and deletions emit
`log_deletion`. Widget values (including many-to-many and split widgets) are
gathered into a form-data dict and re-validated through the same form.

## Theming

Two Textual-native layers compose: a named `Theme` (palette) selected by
`ADMIN_TUI["THEME_NAME"]`, and an optional `.tcss` (`ADMIN_TUI["THEME"]`) layered
on top. No parallel theming abstraction is introduced. See
[theming.md](./theming.md).

## Resilience

DB/query failures (missing table, permission error, broken `ModelAdmin` method)
are caught and surfaced as notifications; the app stays on a usable screen
instead of crashing.

## Where to look next

- [api.md](./api.md) — the public Python surface and stability policy.
- [extending.md](./extending.md) — overlays, hooks, custom widgets and screens.
- [configuration.md](./configuration.md) — the `ADMIN_TUI` settings dict.
- [cli.md](./cli.md) — the management command, flags, and exit codes.
- `sample_project/library/tui.py` — a worked overlay example.
