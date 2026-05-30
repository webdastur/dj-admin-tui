# Implementation Plan: Django Admin TUI — v1

**Branch**: `001-admin-tui-mvp` | **Date**: 2026-05-30 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/001-admin-tui-mvp/spec.md`

## Summary

A pip-installable Django app that drives the existing admin from a Textual TUI.
The package contributes a single `manage.py admin_tui` command. In-process, it
synthesizes a request scoped to a chosen Django user, walks `admin.site._registry`
through a parallel `TuiSite` (auto-synthesizing a `TuiAdmin` overlay when none is
registered), and renders the index, changelist, detail, create/edit, delete, and
admin-action paths by calling the real `ModelAdmin` methods. Permissions and audit
flow entirely through Django's own hooks (`has_*_permission`,
`log_addition/log_change/log_deletion`). The public API surface is fixed at six
names plus documented hooks; everything else is `_internal`. A sample Django project
in the repo registers one overlay, one custom widget, and one TUI-native action and
is exercised by CI as the regression suite for the extension surface.

## Technical Context

**Language/Version**: Python 3.12+. This is the intersection: Django 6.0
requires 3.12+; the package's floor must match its highest-Django dependency.
Lower floors (3.10/3.11) would force us to drop Django 6.0, which is the current
stable as of 2026-05-30 and what FR-036 obliges us to support.

**Primary Dependencies** (latest stable on 2026-05-30, verified from PyPI):

- **Django** — test matrix is 4.2 LTS, 5.2 LTS, 6.0. 5.1/5.0 are EOL since 5.2 LTS
  shipped. See `contracts/internal-django-surface.md` for the admin APIs reused.
- **Textual** `>=8.2,<9` (current stable 8.2.7, released 2026-05-19). The App /
  Screen / DataTable / BINDINGS / CSS_PATH surface this plan relies on has no
  breaking changes vs. 6.x; `Pilot.click` accepts widgets directly now and
  `push_screen` returns an Awaitable (we await it). Textual markup replaced
  Rich markup in v2.0; the `[tag]...[/]` syntax we use is the same in both.
- **rich** — transitive via Textual (current 15.0.0); not pinned by us.

**Dev/test dependencies** (floor only — let CI catch upstream regressions):

- `pytest >=9.0` (current 9.0.3)
- `pytest-django >=4.12` (current 4.12.0 — officially supports the full Django
  matrix above)
- `pytest-asyncio >=1.4` (current 1.4.0 — post-1.0 stable line)
- `hatchling >=1.29` (build backend; current 1.29.0)

No runtime dependencies outside the standard library beyond Django + Textual.

**Storage**: Whatever Django database the host project is using; we do not
introduce a data store.

**Testing**: `pytest`, `pytest-django`, `pytest-asyncio`, Textual's `Pilot`
(headless `async with app.run_test()`), and a tiny in-repo `sample_project/` that
acts as both the dev target and the regression suite for the public API.

**Target Platform**: Any OS with a modern terminal emulator (ANSI color, ≥80×24).
Primary dev targets: Linux + macOS. Windows: best-effort via the Windows Terminal.

**Project Type**: Single Python package (library + management command) shipped
alongside a sample Django project used for tests and docs.

**Performance Goals**: Changelist page-transition p95 under 300 ms against
100k-row tables on a developer laptop (SC-002). Memory use bounded by
`list_per_page`, not table size.

**Constraints**: No network port. No new persistent state. Single-process. The
v1 trust model is "local to whoever can run `manage.py`" (FR-004, FR-005,
Constitution VII).

**Scale/Scope**: One package (`admin_tui/`), one sample project, ~25 modules
across `core/`, `screens/`, `widgets/`, `_internal/`. Public API frozen at the
six names enumerated in FR-030.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Each principle is restated as a binding gate and checked against the design
described above and detailed in `research.md` / `data-model.md` / `contracts/`.

| # | Principle | Gate (must hold true) | Result |
|---|-----------|----------------------|--------|
| I | Reuse Django's admin | No code path computes filtering, validation, or permission logic that Django provides. | ✅ Changelist uses `ModelAdmin.get_changelist_instance(request)`; forms use `get_form(request, obj)`; permissions go straight through `has_*_permission`. See `contracts/internal-django-surface.md`. |
| II | Permission & audit fidelity | Every read passes `has_view_permission`; every mutation passes the relevant `has_*_permission` AND emits a `LogEntry` via the admin's own helpers. | ✅ Detail / create / edit / delete / action paths all gated and audited. `core/audit.py` is a thin pass-through to `log_addition / log_change / log_deletion`. |
| III | Zero-config by default | A project with `ModelAdmin`s and no `tui.py` works fully. | ✅ `TuiSite._synthesize_default(model_admin)` produces an overlay with no required declarations. Sample project includes a "vanilla" app with zero TUI config (SC-001, SC-007). |
| IV | Defaults travel the extension path | Built-in behavior is produced by the same overlay path third-party code uses. | ✅ The synthesized default IS a `TuiAdmin` subclass returned by `TuiSite.get_or_register(model)`; there is no parallel default-renderer branch. |
| V | Small, intentional, stable public API | Public surface = `register`, `TuiAdmin`, `tui_site`, `field_widgets`, `AdminTuiApp`, plus the documented overlay hook methods. Nothing else. | ✅ Codified in `admin_tui/__init__.py.__all__`, enforced by a public-surface test (`tests/test_public_api.py`). See `contracts/public-api.md`. |
| VI | Build on Textual; don't wrap it | Customization hands developers Textual primitives (`Screen`, `Widget`, CSS), not a parallel abstraction. | ✅ `get_changelist_screen` / `get_detail_screen` return Textual `Screen` subclasses. Theming via Textual CSS. No wrapper widgets in the public API. |
| VII | Local-first security posture | No network port, no token, no remote API. Trust model documented. | ✅ Single management command, in-process, stdin/stdout/stderr only. The README and `quickstart.md` lead with the trust statement. |
| VIII | Sample app covers every extension point | Sample registers a `TuiAdmin`, a custom field widget, and a TUI-native action; CI fails if any breaks. | ✅ `sample_project/library/tui.py` exercises overlay + custom action; `sample_project/library/fields.py` + `tui_widgets.py` exercise the widget registry. Tests in `tests/integration/sample_project/`. |

**Result**: PASS. No violations to record in Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/001-admin-tui-mvp/
├── plan.md              # This file (/speckit-plan command output)
├── spec.md              # Feature spec (already written)
├── research.md          # Phase 0 output — locked decisions w/ rationale & alternatives
├── data-model.md        # Phase 1 output — entities, relationships, state
├── quickstart.md        # Phase 1 output — install / first launch / first overlay
├── contracts/           # Phase 1 output — public API + CLI + settings + internal admin surface
│   ├── public-api.md            # FR-030 surface, signatures, semver
│   ├── cli.md                   # `manage.py admin_tui` flags, exit codes
│   ├── settings.md              # `ADMIN_TUI` dict schema
│   └── internal-django-surface.md  # The ModelAdmin / request methods we depend on
├── checklists/
│   └── requirements.md  # 16/16 passing (already validated)
└── tasks.md             # Phase 2 output (created by /speckit-tasks, not by this command)
```

### Source Code (repository root)

```text
admin_tui/                       # the installable package
├── __init__.py                  # public API re-exports ONLY: register, TuiAdmin,
│                                # tui_site, field_widgets, AdminTuiApp, hook protocols
├── apps.py                      # AppConfig; ready() calls _autodiscover.autodiscover()
├── sites.py                     # TuiSite registry + default singleton `tui_site`
│                                # + _synthesize_default(model_admin) → TuiAdmin
├── options.py                   # TuiAdmin (public base class) + @register decorator
├── app.py                       # AdminTuiApp (subclassable Textual App)
├── conf.py                      # ADMIN_TUI settings loader, defaults, validation
├── management/
│   └── commands/
│       └── admin_tui.py         # CLI entry point: parse --user / --app, build request,
│                                # launch AdminTuiApp.run()
├── screens/                     # Default Textual screens (also the extension shape)
│   ├── __init__.py
│   ├── index.py                 # IndexScreen — apps → models
│   ├── changelist.py            # ChangelistScreen — DataTable + search/filter/sort/page
│   ├── change.py                # ChangeScreen — detail + create/edit form
│   └── action_confirm.py        # ActionConfirmScreen — confirm + run actions / delete
├── widgets/                     # Field-class → Textual-widget registry + defaults
│   ├── __init__.py
│   ├── registry.py              # FieldWidgetRegistry (public: `field_widgets`)
│   └── defaults/                # text / bool / choice / fk / date / datetime / json / numeric
│       ├── __init__.py
│       ├── text.py
│       ├── boolean.py
│       ├── choice.py
│       ├── foreign_key.py
│       ├── datetime.py
│       └── json_field.py
├── core/                        # Internal (underscore-prefixed module names externally
│                                # — keep names short here; visibility enforced by __all__)
│   ├── __init__.py
│   ├── request.py               # build_request(user, query=None) — the synthetic request
│   ├── messages.py              # _CapturingMessageStorage (BaseStorage subclass)
│   ├── changelist.py            # _build_changelist(model_admin, request, **q)
│   ├── forms.py                 # _render_form(model_admin, request, obj=None) → bound form
│   ├── actions.py               # _run_action(model_admin, request, action, queryset)
│   ├── audit.py                 # _log_addition/_log_change/_log_deletion thin pass-throughs
│   └── permissions.py           # _check(action, model_admin, request, obj=None)
├── _internal/                   # Strictly underscored — not re-exported from `admin_tui`
│   ├── __init__.py
│   ├── autodiscover.py          # autodiscover_modules("tui")
│   └── public_api.py            # `_PUBLIC_NAMES` constant; surface-freezing test reads this
└── py.typed                     # PEP 561 marker — we ship type hints

sample_project/                  # in-repo Django project (NOT installed by pip)
├── manage.py
├── sample_project/
│   ├── __init__.py
│   ├── settings.py              # MINIMAL: SQLite, admin enabled, ADMIN_TUI={}
│   └── urls.py
├── library/                     # one app, one ModelAdmin, one TuiAdmin overlay
│   ├── __init__.py
│   ├── apps.py
│   ├── models.py                # Book, Author, Tag (FK + M2M + JSON + a custom ColorField)
│   ├── admin.py                 # Standard ModelAdmin with list_display/search/filters/actions
│   ├── tui.py                   # TuiAdmin overlay: row action + key binding + render override
│   ├── fields.py                # ColorField (custom)
│   └── tui_widgets.py           # ColorPickerWidget registered for ColorField
└── plain_app/                   # one app with NO tui.py — exercises FR-021 (zero-config)
    ├── __init__.py
    ├── apps.py
    ├── models.py
    └── admin.py

tests/                           # NOT inside admin_tui/ — keeps test deps out of the wheel
├── conftest.py                  # pytest-django config; sample_project on sys.path
├── unit/
│   ├── test_request.py          # synthetic request + _CapturingMessageStorage
│   ├── test_widget_registry.py  # MRO walk, per-model overrides
│   ├── test_default_synthesis.py  # zero-config path → working TuiAdmin
│   └── test_public_api.py       # __all__ in admin_tui/__init__.py == _PUBLIC_NAMES (FR-030)
└── integration/
    └── sample_project/
        ├── test_index.py        # FR-009 / SC-003 — index respects permissions
        ├── test_changelist.py   # FR-010..012 — search, filter, sort, paginate
        ├── test_crud.py         # FR-013..016 — create/edit/delete + LogEntry parity
        ├── test_actions.py      # FR-017..019 — actions + message_user capture
        ├── test_overlay.py      # FR-020..024 — TuiAdmin + widget + native action (US4)
        └── test_cli.py          # FR-001..003 — invalid --user fails in <1s (SC-008)

docs/
├── README.md                    # repo entry; trust model (FR-005) called out up top
├── quickstart.md                # also linked from specs/.../quickstart.md
└── architecture.md              # one diagram + the synthetic-request explainer

pyproject.toml                   # PEP 621 + uv project metadata; pinned ranges
.python-version                  # 3.12 (uv reads this)
uv.lock                          # committed (FR-035 reproducible installs)
LICENSE                          # MIT (FR-037)
```

**Structure Decision**: Single Python package (`admin_tui/`) with a parallel
in-repo `sample_project/` and a top-level `tests/`. This matches the "single
project" template from the plan template and reflects the fact that everything
ships in one wheel except the sample project (a dev/test asset, not a package
dependency). The `_internal/` directory and `_PUBLIC_NAMES` enforcement codify
Constitution V at the filesystem level so the public-surface test cannot drift
silently.

## Complexity Tracking

> Fill ONLY if Constitution Check has violations that must be justified.

No constitution violations. The two design choices that *could* look like
complexity — the `_internal/` directory and the centralized synthetic-request
builder — are both load-bearing for principles (V and II) and have no simpler
alternative that preserves the invariant: a single registry of public names
prevents drift, and a single request factory means every code path that touches
the admin goes through one auditable choke point.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| *(none)*  | —          | —                                   |
