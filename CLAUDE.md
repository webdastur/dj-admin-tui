# Django Admin TUI — project notes

A Textual terminal UI that drives the Django admin. **Core rule: reuse Django's
admin; never reimplement it.** Querysets, search, filtering, ordering,
pagination, form construction, validation, permissions, actions, and audit all
come from the registered `ModelAdmin` and Django's own internals. The TUI only
renders that output in the terminal and adds presentation/interaction.

## Layout

- `admin_tui/` — the package.
  - `app.py` — `AdminTuiApp` (Textual App); registers themes, applies `THEME_NAME`.
  - `conf.py` — the `ADMIN_TUI` settings loader/validation.
  - `sites.py` / `options.py` — `TuiSite` registry + `TuiAdmin` overlay (+ `@register`).
  - `screens/` — `index`, `changelist`, `change`, `action_confirm`.
  - `widgets/` — `layout.py` (fixed-width columns + truncation), `filters.py`
    (filter sidebar from Django's `get_filters`), `registry.py` + `defaults/`
    (field → Textual widget).
  - `themes/` — bundled `django` / `django-dark` Textual `Theme`s.
  - `core/` — synthetic request, changelist/form/action bridges, audit, permissions.
- `sample_project/` — in-repo Django project used by the tests.
- `tests/` — `unit/` + `integration/sample_project/` (pytest + Textual `Pilot`).
- `docs/` — user/developer docs (start at `docs/README.md`).

## Conventions

- Public API is five names only: `register`, `TuiAdmin`, `tui_site`,
  `field_widgets`, `AdminTuiApp`. Everything else under `admin_tui.*` is
  internal. A test freezes this surface (`tests/unit/test_public_api.py`).
- Changelist columns are fixed-width and selection-independent; cells are
  pre-truncated (`widgets/layout.py`). Never let `DataTable` auto-size.
- Sorting/filtering defer to Django (`get_ordering_field_columns`,
  `get_ordering_field`, `get_filters`).
- DB/query errors surface as notifications — never crash the app.
- Run tests with `python -m pytest -q`; lint with `ruff`.
