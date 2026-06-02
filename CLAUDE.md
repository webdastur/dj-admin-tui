# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Textual terminal UI that drives the Django admin (browse, search, filter, sort,
create, edit, delete, run admin actions) from the terminal. Distribution name is
`dj-admin-tui`; the import package is `dj_admin_tui`. The management command stays
`manage.py admin_tui` and the settings dict key stays `ADMIN_TUI`. User/developer
docs live in `docs/` (a MkDocs Material site; start at `docs/index.md`).

**Core rule — reuse Django's admin; never reimplement it.** Querysets, search,
filtering, ordering, pagination, form construction, validation, permissions,
actions, and audit are all produced by the registered `ModelAdmin` and Django's
own internals (`get_changelist_instance`, `get_form`, `get_filters`,
`get_ordering_field_columns`, `has_*_permission`, `log_addition/change/deletion`).
The TUI renders that output and adds presentation/interaction only. If you find
yourself re-deriving admin behaviour, stop — bridge to Django instead.

## Commands

```bash
# Tests (pytest + Textual Pilot; Django settings come from pyproject)
python -m pytest -q
python -m pytest tests/integration/sample_project/test_save_matrix.py   # one file
python -m pytest -k m2m                                                  # by name

# Lint / format (CI runs these with no path args, i.e. the whole repo)
ruff check
ruff format --check

# Docs (MkDocs Material)
uv run --extra docs mkdocs serve              # live preview
uv run --extra docs mkdocs build --strict     # what the docs build verifies

# Run the TUI against the in-repo sample project
python sample_project/manage.py migrate        # first run / after model changes
python sample_project/manage.py createsuperuser
python sample_project/manage.py admin_tui      # add --user <name> / --theme-name <name>

# Sample-project migrations (when sample_project/library/models.py changes)
python sample_project/manage.py makemigrations library
```

The venv is at `.venv/`. `DJANGO_SETTINGS_MODULE=sample_project.sample_project.settings`
is set in `pyproject.toml`, so pytest and the sample `manage.py` both find it.

## Architecture

```
AdminTuiApp (Textual App, app.py)   loads styles.tcss + theme; pushes Screens
  IndexScreen        apps → models (permission-scoped)
  ChangelistScreen   DataTable + search + sort + filter sidebar + pagination
  ChangeScreen       detail / create / edit (admin fieldsets + field widgets)
  ActionConfirmScreen  confirm + run admin actions / delete

TuiSite (sites.py)     model → TuiAdmin overlay; synthesizes a default overlay
                       from the ModelAdmin when none is registered
TuiAdmin (options.py)  per-model overlay; delegates to self.model_admin
FieldWidgetRegistry (widgets/registry.py)  form-field class → Textual widget (MRO walk)
core/                  synthetic request (request.py), changelist/form/action
                       bridges, audit.py, permissions.py
```

- **Synthetic request** (`core/request.py`): the single choke point. Every admin
  call gets one `HttpRequest` scoped to the session user, carrying a capturing
  message store. This is why permissions/audit match the web admin.
- **Defaults travel the extension path**: the default overlay IS a synthesized
  `TuiAdmin`, and screens are always chosen via `overlay.get_*_screen(...)`. There
  is no privileged internal render path. A project with `ModelAdmin`s and no
  `tui.py` works fully (zero-config); `tui.py` is autodiscovered like `admin.py`.

## Invariants (do not break)

- **Public API is exactly five names**: `register`, `TuiAdmin`, `tui_site`,
  `field_widgets`, `AdminTuiApp`. Everything else under `dj_admin_tui.*` is internal.
  `tests/unit/test_public_api.py` freezes this; adding a name needs justification +
  test + docs.
- **All styling lives in `dj_admin_tui/styles.tcss`** — the single design system.
  Screens carry no `DEFAULT_CSS`; they compose shared ids/classes (`.atui-btn*`,
  `.atui-breadcrumb`, …). Colours use theme variables. The user's
  `ADMIN_TUI["THEME"]` `.tcss` is layered on top via `App.CSS_PATH`.
- **Changelist columns are fixed-width and selection-independent**, cells
  pre-truncated (`widgets/layout.py`). Never let `DataTable` auto-size columns —
  that reintroduces the "cropped column / expand-on-select" glitch.
- **Sorting/filtering defer to Django** (`get_ordering_field_columns`,
  `get_ordering_field`, `get_filters`) — never compute predicates locally.
- **Errors never crash the app**: DB/query failures surface as Textual
  notifications and leave the operator on a usable screen.
- **Save path mirrors the admin**: `get_form` → `is_valid` → `save_model` →
  `save_related` → `log_addition/log_change`; deletes go through `log_deletion`.

## Testing notes

- Integration tests drive the real app headlessly with Textual `Pilot`
  (`async with app.run_test(...) as pilot`). Pilot runs the App in a **worker
  thread**, so tests that launch the App must use the `transactional_db` fixture
  (NOT `db`) — the App's connection only sees committed rows.
- `AdminTuiApp.__init__` sets `DJANGO_ALLOW_ASYNC_UNSAFE` so the sync ORM works
  inside Textual's event loop.
- `tests/conftest.py` puts the repo root on `sys.path` so `sample_project` imports.
- Markers are `--strict-markers`; only `slow` is registered.
