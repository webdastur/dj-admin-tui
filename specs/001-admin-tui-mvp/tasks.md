---

description: "Task list for Django Admin TUI v1 implementation"
---

# Tasks: Django Admin TUI — v1

**Input**: Design documents from `specs/001-admin-tui-mvp/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`,
`contracts/{public-api,cli,settings,internal-django-surface}.md`, `quickstart.md`.

**Tests are INCLUDED** for this feature. The spec's `Measurable Outcomes`
(SC-001 — SC-008) and the constitution (Principle VIII — "an untested
extension point is an undocumented, unkept promise") mandate automated
coverage; we therefore generate test tasks alongside implementation tasks
per phase.

**Organization**: Tasks are grouped by user story so each story can be
independently implemented, tested, and demonstrated as an MVP increment.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1 / US2 / US3 / US4) —
  Setup, Foundational, and Polish phases carry no story label.
- Every task includes the exact file path it touches.

## Path Conventions

Per `plan.md` § Project Structure:

- Package source: `admin_tui/...`
- Sample project: `sample_project/...`
- Tests: `tests/unit/...` and `tests/integration/sample_project/...`
- Docs: `docs/...`
- Repo root holds `pyproject.toml`, `uv.lock`, `LICENSE`, `README.md`,
  `.python-version`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project layout, packaging, lint/format, CI matrix, and the
sample-project / test scaffolding.

- [X] T001 Create top-level project directories per `plan.md` § Project Structure: `admin_tui/`, `admin_tui/core/`, `admin_tui/_internal/`, `admin_tui/screens/`, `admin_tui/widgets/`, `admin_tui/widgets/defaults/`, `admin_tui/management/commands/`, `sample_project/sample_project/`, `sample_project/library/`, `sample_project/plain_app/`, `tests/unit/`, `tests/integration/sample_project/`, `docs/` — each with an empty `__init__.py` where applicable.
- [X] T002 [P] Write `LICENSE` (MIT, FR-037) at the repo root.
- [X] T003 [P] Write `.python-version` containing `3.12` at the repo root.
- [X] T004 [P] Write `.gitignore` at the repo root covering `__pycache__/`, `*.py[cod]`, `.venv/`, `dist/`, `build/`, `*.egg-info/`, `.coverage`, `htmlcov/`, `.pytest_cache/`, `.ruff_cache/`, `db.sqlite3`, `.admin_tui_debug.log`.
- [X] T005 Write `pyproject.toml` at the repo root: PEP 621 metadata, `[build-system] requires = ["hatchling>=1.29"]`, hatchling backend, `requires-python = ">=3.12"`, runtime deps (`django>=4.2,<7`, `textual>=8.2,<9`), `[project.optional-dependencies] dev` (`pytest>=9.0`, `pytest-django>=4.12`, `pytest-asyncio>=1.4`, `ruff>=0.14`), tool sections for ruff (lint+format) and pytest (`DJANGO_SETTINGS_MODULE=sample_project.sample_project.settings`, `asyncio_mode=auto`, `testpaths=["tests"]`). Honor versions from `plan.md` § Primary Dependencies exactly.
- [X] T006 [P] Write `.github/workflows/ci.yml`: matrix `python-version: ["3.12", "3.13", "3.14"]` × `django-version: ["4.2", "5.2", "6.0"]` with `exclude` entries for cells the upstream matrices forbid (Django 4.2 on 3.13/3.14; Django 5.2 on 3.14). Steps: checkout, `astral-sh/setup-uv`, `uv sync`, install pinned Django per matrix cell, `uv run ruff check && uv run ruff format --check`, `uv run pytest -q`. Reference `research.md` § R1/R2 for the matrix justification.
- [X] T007 Run `uv sync` to materialize `.venv/` and create `uv.lock`; commit `uv.lock` (FR-035 reproducible installs). This task BLOCKS on T005.

### Sample-project scaffolding (Django side of Setup)

- [X] T008 [P] Write `sample_project/manage.py` — standard Django entry point pointing at `sample_project.sample_project.settings`.
- [X] T009 [P] Write `sample_project/sample_project/__init__.py` (empty) and `sample_project/sample_project/asgi.py` / `wsgi.py` (stock Django boilerplate).
- [X] T010 [P] Write `sample_project/sample_project/settings.py` — SQLite `db.sqlite3` under repo root, `INSTALLED_APPS = ["django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes", "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles", "admin_tui", "sample_project.library", "sample_project.plain_app"]`, minimal middleware (admin needs `SessionMiddleware`, `AuthenticationMiddleware`, `MessageMiddleware`), `USE_TZ=True`, `TIME_ZONE="UTC"`, `SECRET_KEY="sample-not-secret"`, `DEBUG=True`, `ADMIN_TUI = {}` (zero-config — exercises FR-021).
- [X] T011 [P] Write `sample_project/sample_project/urls.py` — only `admin/` URL pattern; the TUI is reached via management command, not HTTP.
- [X] T012 [P] Write `tests/conftest.py`: prepend repo root + `sample_project/` to `sys.path`; set `DJANGO_SETTINGS_MODULE`; export a `django_db_setup` no-op override if needed to keep unit tests fast; add a `superuser` and `staff_only_user` fixture that mark `pytest.mark.django_db`.
- [~] T013 [P] Write `pytest.ini` *only if* `pyproject.toml`'s `[tool.pytest.ini_options]` does not cover what's needed; otherwise note in T005 that `pyproject.toml` is the source of truth.

**Checkpoint**: A `uv sync` succeeds, `uv run pytest --collect-only` discovers an empty test set, and `uv run python sample_project/manage.py check` returns no errors.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build the entire public + internal core surface so every user-story
phase can plug in. This includes the public 6-name API, autodiscovery, the
synthetic-request stack, the TuiSite registry with default-overlay synthesis,
the TuiAdmin base class with all documented hooks, the widget registry with
default widgets, the AdminTuiApp shell, the CLI entry point with --user
resolution and exit codes, and the foundational tests that pin the public
contract.

**⚠️ CRITICAL**: No user-story work can begin until this phase is complete.

### Public surface scaffolding

- [X] T014 [P] Write `admin_tui/_internal/__init__.py` (empty) and `admin_tui/_internal/public_api.py` defining `_PUBLIC_NAMES = ("register", "TuiAdmin", "tui_site", "field_widgets", "AdminTuiApp")` (FR-030, Constitution V).
- [X] T015 [P] Write `admin_tui/py.typed` (empty file; PEP 561 marker).

### Core: synthetic request, messages, permissions

- [X] T016 [P] Write `admin_tui/core/__init__.py` (empty).
- [X] T017 [P] Write `admin_tui/core/messages.py` implementing `_CapturingMessageStorage(BaseStorage)` with `_get` returning `([], True)`, `_store` returning `[]`, and `add(level, message, extra_tags="")` appending `(level, str(message), extra_tags)` to `self.captured`. Per `research.md` § R3.
- [X] T018 Write `admin_tui/core/request.py` exposing `build_request(user, query=None, *, path="/")` per `research.md` § R3 — uses `django.test.RequestFactory`, attaches `request.user = user` and `request._messages = _CapturingMessageStorage(request)`. Marker attribute `request._tui_session = None` reserved for `TuiSession` attachment in T037. Depends on T017.
- [X] T019 [P] Write `admin_tui/core/permissions.py` exposing `_check(action: Literal["view","add","change","delete"], model_admin, request, obj=None) -> bool` — delegates to `model_admin.has_*_permission(...)`. No "TUI permission" concept (Constitution II).

### Settings loader and autodiscovery

- [X] T020 Write `admin_tui/conf.py` per `contracts/settings.md`: read `getattr(settings, "ADMIN_TUI", {})` once on `AppConfig.ready()`; apply defaults (`APP_CLASS`, `PAGE_SIZE=50`, `THEME=None`, `AUTODISCOVER=True`, `COMPAT_WARNINGS=True`); raise `ImproperlyConfigured` on unknown keys or invalid values (PAGE_SIZE bounds, THEME path existence, APP_CLASS subclass check deferred until T034). Freeze the result on a module-level `_loaded` dict.
- [X] T021 [P] Write `admin_tui/_internal/autodiscover.py` exposing `autodiscover()` which calls `django.utils.module_loading.autodiscover_modules("tui")`. Skip if `_loaded["AUTODISCOVER"]` is False. Per `research.md` § R10.
- [X] T022 Write `admin_tui/apps.py` defining `AdminTuiConfig(AppConfig)` with `name = "admin_tui"`, `default_auto_field = "django.db.models.BigAutoField"`, and `ready()` that calls `conf._load()` then `autodiscover.autodiscover()`. Depends on T020, T021.

### TuiSite registry + TuiAdmin base + register decorator

- [X] T023 Write `admin_tui/sites.py` defining `TuiSite` with `_registry: dict[Model, TuiAdmin]`, `_screens: dict[str, type[Screen]]`, `_synth_cache: dict[ModelAdmin, TuiAdmin]`. Methods: `register(model, overlay_cls=None)`, `unregister(model)`, `is_registered(model)`, `register_screen(slug, screen_cls)`, `get_or_synthesize(model)`, `models_for(request)`. Synthesis: look up `admin.site._registry[model]`, instantiate the overlay class via `TuiAdmin._synthesize(model_admin)` (T024) and cache. Define module-level `tui_site = TuiSite()`. Per `data-model.md` § 2 and `research.md` § R9. Depends on T019.
- [X] T024 Write `admin_tui/options.py` defining `TuiAdmin` with all declarative slots and hook methods from `contracts/public-api.md` § 2 (init takes `model_admin`, all hooks default-delegate to `self.model_admin`, permission methods delegate). Also defines `_synthesize(cls, model_admin) -> TuiAdmin` classmethod returning `cls(model_admin)` so subclasses inherit it. Define `register(*models, site=tui_site)` decorator wiring into `tui_site.register(...)`. Per `data-model.md` § 3 and `contracts/public-api.md` § 1. Depends on T023.

### Field-widget registry + default widgets

- [X] T025 [P] Write `admin_tui/widgets/__init__.py` (empty for now; will re-export `field_widgets` in T036).
- [X] T026 [P] Write `admin_tui/widgets/registry.py` defining `FieldWidgetRegistry` with `_table: dict[type[models.Field], Callable]`, `_resolved_cache`. Methods: `register(field_cls, factory)` (also usable as decorator), `is_registered(field_cls)`, `resolve(bound_field, overlay=None)` that (a) checks overlay's `field_widgets`, (b) walks `type(bound_field.field).__mro__` against `_table`, (c) falls back to a text widget. Define `field_widgets = FieldWidgetRegistry()`. Per `data-model.md` § 4.
- [X] T027 [P] Write `admin_tui/widgets/defaults/text.py` — `text_widget(bound_field)` returns a Textual `Input` widget bound to `bound_field.value()`. Handles `forms.CharField`, `forms.EmailField`, `forms.URLField`, `forms.SlugField`.
- [X] T028 [P] Write `admin_tui/widgets/defaults/boolean.py` — Textual `Switch` for `forms.BooleanField` / `forms.NullBooleanField`.
- [X] T029 [P] Write `admin_tui/widgets/defaults/choice.py` — Textual `Select` populated from `bound_field.field.choices`. Handles `forms.ChoiceField` and `forms.TypedChoiceField`.
- [X] T030 [P] Write `admin_tui/widgets/defaults/foreign_key.py` — autocomplete-style widget over `bound_field.field.queryset`, scoped by the related `ModelAdmin`'s `get_queryset(request)` and `has_view_permission`.
- [X] T031 [P] Write `admin_tui/widgets/defaults/datetime.py` — Textual `Input` with parse/format helpers for `forms.DateField`, `forms.TimeField`, `forms.DateTimeField`, surfacing `ValidationError`s as field errors.
- [X] T032 [P] Write `admin_tui/widgets/defaults/json_field.py` — multi-line Textual `TextArea` bound to JSON-encoded value of `forms.JSONField`; commits parse to the form's clean step.
- [X] T033 [P] Write `admin_tui/widgets/defaults/numeric.py` — `forms.IntegerField`, `forms.FloatField`, `forms.DecimalField` via `Input` with parse helpers.
- [X] T034 Write `admin_tui/widgets/defaults/__init__.py` — imports each default module and calls `field_widgets.register(...)` for each mapping. Depends on T026 — T033.

### App shell + CLI entry point

- [X] T035 Write `admin_tui/app.py` defining `AdminTuiApp(textual.app.App)` with `__init__(*, session: TuiSession)` storing the session and (if `session.theme_path` is set) assigning `self.CSS_PATH = str(session.theme_path)` BEFORE calling `super().__init__()`, default `BINDINGS = [("q", "quit", "Quit"), ("?", "show_help", "Help")]`, and `on_mount` that pushes `IndexScreen(session)` (T050). Provide `_screen_for_changelist(overlay, request)` and `_screen_for_detail(overlay, request, obj=None)` helpers that consult `overlay.get_changelist_screen(request)` and `overlay.get_detail_screen(request, obj)` (Constitution IV — defaults travel the extension path). Depends on T024.
- [X] T036 Write `admin_tui/__init__.py` re-exporting exactly `register`, `TuiAdmin`, `tui_site`, `field_widgets`, `AdminTuiApp` and setting `__all__` from `_internal.public_api._PUBLIC_NAMES`. Depends on T014, T024, T026, T035.
- [X] T037 Write `admin_tui/management/__init__.py` and `admin_tui/management/commands/__init__.py` (both empty), then write `admin_tui/management/commands/admin_tui.py` per `contracts/cli.md`: a `BaseCommand` with `add_arguments` for `--user`, `--app`, `--theme`, `--no-color`, `--debug`. In `handle`: resolve `--user` per the rules (exit codes 2 / 3), import `--app` (code 4) or use `_loaded["APP_CLASS"]`, validate `--theme` path (code 5), build `TuiSession(user=..., started_at=now(), theme_path=..., app_class=...)` and call `app_class(session=session).run()`. Resolution failures print one-line stderr messages and return non-zero BEFORE constructing the app (SC-008). Depends on T020, T024, T035.

### Sample-project app + ModelAdmin registrations

- [X] T038 [P] Write `sample_project/library/__init__.py` (sets `default_app_config = "sample_project.library.apps.LibraryConfig"`).
- [X] T039 [P] Write `sample_project/library/apps.py` defining `LibraryConfig(AppConfig)` with `name = "sample_project.library"`.
- [X] T040 [P] Write `sample_project/library/models.py` defining: `Tag(name)`, `Author(name, bio: TextField, born: DateField)`, `Book(title, author: FK->Author, tags: M2M->Tag, summary: TextField, published: DateField, featured: BooleanField, metadata: JSONField)`. Migrations run in T043.
- [X] T041 [P] Write `sample_project/library/admin.py` registering standard `ModelAdmin` classes: `BookAdmin` with `list_display=("title", "author", "published", "featured")`, `search_fields=("title", "author__name")`, `list_filter=("featured", "published")`, `actions=("mark_featured_action", "archive_selected_action")` and two custom actions — `mark_featured_action(modeladmin, request, queryset)` bulk-updating `featured=True` and calling `modeladmin.message_user(request, ...)`, and `archive_selected_action(modeladmin, request, queryset)` bulk-updating an `archived` flag (Book gains an `archived: BooleanField(default=False)` for this purpose; reflect in T040); `AuthorAdmin` with `list_display=("name", "born")`, `search_fields=("name",)`; `TagAdmin` minimal.
- [X] T042 [P] Write `sample_project/plain_app/__init__.py`, `apps.py`, `models.py` (with one trivial `Note(title, body)` model), `admin.py` (basic `ModelAdmin`). **No `tui.py` file** — exercises FR-021 zero-config (SC-001). Migrations run in T043.
- [X] T043 Run `uv run python sample_project/manage.py makemigrations library plain_app` and commit the generated `migrations/` directories. Then `uv run python sample_project/manage.py migrate` against the local SQLite. Depends on T040, T042, T007.

### Foundational tests — pin the contract

- [X] T044 [P] Write `tests/unit/test_public_api.py` asserting `set(admin_tui.__all__) == set(admin_tui._internal.public_api._PUBLIC_NAMES) == {"register", "TuiAdmin", "tui_site", "field_widgets", "AdminTuiApp"}`, and asserting each name resolves to an importable object. FR-030 freezer.
- [X] T045 [P] Write `tests/unit/test_request.py` asserting `build_request(user)` returns an `HttpRequest` with `.user is user`, `request._messages` is a `_CapturingMessageStorage`, and `add_message(request, INFO, "x")` lands in `request._messages.captured`. Per `research.md` § R3.
- [X] T046 [P] Write `tests/unit/test_widget_registry.py` asserting (a) MRO walk: a subclass of `models.JSONField` resolves to the JSONField widget; (b) overlay `field_widgets` override beats the global registry; (c) unknown field type falls through to the text-input default.
- [X] T047 [P] Write `tests/unit/test_default_synthesis.py` asserting that `tui_site.get_or_synthesize(plain_app.models.Note)` returns a `TuiAdmin` instance with `model_admin` pointing at the registered `NoteAdmin`, and that subsequent calls return the same instance (synth cache, `data-model.md` § 2).
- [X] T048 [P] Write `tests/integration/sample_project/test_cli.py` asserting (a) `manage.py admin_tui --user nonexistent` exits with code 2 and prints a one-line error within 1 second (SC-008); (b) `--user` resolving an inactive user exits with code 2; (c) `--user` resolving a non-staff user exits with code 2; (d) `--app pkg.does_not_exist:NotAClass` exits with code 4; (e) no superuser → code 3. Use `subprocess.run(..., timeout=2)` to enforce the time bound.

**Checkpoint**: Foundation ready. Every public name exists and is enforced by a
test. The CLI exits cleanly on every invalid input. The sample project boots
to a Django admin shell. User-story phases can now begin in parallel.

---

## Phase 3: User Story 1 — Operator browses admin data (Priority: P1) 🎯 MVP

**Goal**: Read-only operator workflow — index → changelist → detail, fully
honoring permissions and matching the web admin's result sets.

**Independent Test**: Launch `manage.py admin_tui` against `sample_project` as
the superuser; assert every registered model is in the index. Launch as a
view-only user on `Book`; assert only `Book` is visible. Run search / filter /
sort / pagination; assert result sets match what `BookAdmin.get_changelist_instance(...)`
would return under the same parameters in the web admin (SC-001, SC-003).

### Implementation for User Story 1

- [ ] T049 [P] [US1] Write `admin_tui/screens/__init__.py` (empty).
- [ ] T050 [US1] Write `admin_tui/screens/index.py` defining `IndexScreen(Screen)`. `compose()` yields a Textual `ListView` of apps → models. `on_mount` calls `tui_site.models_for(request)` (which itself filters by `has_module_permission` + `has_view_permission`). Pressing Enter on a row navigates to `_screen_for_changelist(...)`. Depends on T035.
- [ ] T051 [US1] Write `admin_tui/core/changelist.py` exposing `_build_changelist(model_admin, request, *, query: dict | None = None)` that calls `model_admin.get_changelist_instance(request)` (Constitution I, `research.md` § R4) after mutating `request.GET` to include the query params. Returns the `ChangeList` instance.
- [ ] T052 [US1] Write `admin_tui/screens/changelist.py` defining `ChangelistScreen(Screen)`. State: `overlay`, `query` (search/filter/sort/page). `compose()` yields a Textual `DataTable` (`cursor_type="row"`, `zebra_stripes=True`) plus a header showing the model verbose name and a footer with search/filter/sort/page key bindings. `on_mount`: build the changelist via `_build_changelist`, populate columns from `overlay.get_list_columns(request)`, populate rows by iterating `changelist.result_list` and calling `overlay.render_cell(request, obj, field)` for each cell. Keys: `/` opens search input, `f` opens filter sidebar, `s` cycles sort on the focused column, PgUp / PgDn page, Enter opens detail. Each state change rebuilds the changelist (correct because Django's `ChangeList` is the source of truth — Constitution I). Depends on T051.
- [ ] T053 [US1] Write `admin_tui/screens/change.py` defining `ChangeScreen(Screen)` with read-only mode (US2 extends with create/edit). `compose()` renders the object's fieldsets per `overlay.detail_fieldsets` (default delegates to `model_admin.get_fieldsets(request, obj)`), using the widget registry to resolve a *display-only* form rendering. Header shows object_repr. Bindings: `e` (edit — disabled until US2), `q` back to changelist. Depends on T052.
- [ ] T054 [US1] In `admin_tui/app.py`, wire `_screen_for_changelist` and `_screen_for_detail` to dispatch through `overlay.get_changelist_screen(request)` / `overlay.get_detail_screen(request, obj)` — the defaults from T035 return `ChangelistScreen` / `ChangeScreen`, but overlays can override (this is what US4 exercises — Constitution IV / VI). Depends on T035, T052, T053.

### Tests for User Story 1

- [ ] T055 [P] [US1] Write `tests/integration/sample_project/test_index.py` asserting (FR-009, SC-003): (a) superuser session sees all registered apps + models; (b) a `view`-only-on-Book user sees `library/Book` and nothing else; (c) an inactive ModelAdmin (none registered for `Note` from `plain_app`'s perspective is N/A — verify zero-config: `Note` IS in the index because `plain_app/admin.py` registers it). Use the `superuser` fixture + a programmatically-created scoped-perms user. Drive the App via `async with AdminTuiApp(session=...).run_test() as pilot:` and assert on the rendered `ListView`'s items.
- [ ] T056 [P] [US1] Write `tests/integration/sample_project/test_changelist.py` (FR-010 — 012, SC-001, SC-002): (a) columns shown match `BookAdmin.get_list_display(...)`; (b) typing `/` then `Tolkien` and pressing Enter narrows rows to ones matching `search_fields`; (c) toggling `featured=True` via the filter sidebar narrows to featured rows; (d) cycling sort by column produces ascending / descending order; (e) page boundaries match `list_per_page`. For each assertion, compare TUI result set against `BookAdmin.get_changelist_instance(request).result_list` for the same parameters — that's the SC-001 "indistinguishable from the web admin" gate.

**Checkpoint**: User Story 1 fully functional and independently testable. The MVP is shippable from here.

---

## Phase 4: User Story 2 — Operator creates and edits records (Priority: P2)

**Goal**: Full create + edit workflow using the admin's `ModelForm`, with admin
validation, `readonly_fields` enforcement, and audit-log parity.

**Independent Test**: Create a `Book` via the TUI; assert `Book.objects.count()`
increased by 1 and a `LogEntry` was written with the session user, the
content type, and a change message constructed by `construct_change_message`.
Trigger a `clean_*` validation error; assert the field-level error is shown
and the record is not saved. Edit a model with `readonly_fields = ("created",)`;
assert the field is shown but not editable, and saving works without touching
the protected field (FR-013 / FR-014 / FR-015, SC-004).

### Implementation for User Story 2

- [ ] T057 [US2] Write `admin_tui/core/forms.py` exposing `_build_form(model_admin, request, *, obj=None) -> ModelForm` calling `model_admin.get_form(request, obj=obj, change=obj is not None)`. Also `_iter_bound_fields(form)` yielding `(name, bound_field)` for fieldset rendering. Per `research.md` § R5. Depends on T026.
- [ ] T058 [US2] Write `admin_tui/core/audit.py` exposing `_log_addition(model_admin, request, obj, change_message)`, `_log_change(model_admin, request, obj, change_message)`, `_log_deletion(model_admin, request, obj)` — each a thin pass-through to the corresponding `model_admin.log_*` method. Also `_change_message(model_admin, request, form, formsets, *, add)` calling `model_admin.construct_change_message(...)`. Per `research.md` § R7, SC-004.
- [ ] T059 [US2] Extend `admin_tui/screens/change.py` adding create + edit modes: bind the form returned by `_build_form` to the screen state; submit handler runs `form.is_valid()`, surfaces errors on a per-bound-field basis using the widget the field was rendered with (Constitution I — no reimplementation of validation), and on success calls `overlay.before_save(...)`, `model_admin.save_model(request, obj, form, change=...)`, `_log_addition` / `_log_change`, `overlay.after_save(request, obj, created=not change)`. New bindings: `a` (add — only if `has_add_permission`), `Ctrl+S` save, `Esc` cancel. Depends on T057, T058.

### Tests for User Story 2

- [ ] T060 [P] [US2] Add a custom validator to `sample_project/library/models.py`: a `clean_isbn` style method on `BookAdmin` (define a `BookForm(ModelForm)` with `clean_title` rejecting `"forbidden"`); register via `BookAdmin.form = BookForm`. (This is a sample-project change, not an admin_tui change — keeps the test fixture explicit.) Migration not required (form-only change).
- [ ] T061 [P] [US2] Write/extend `tests/integration/sample_project/test_crud.py` (FR-013 — 015, SC-004): (a) create a `Book` with valid data → `Book.objects.count()` +1 and `LogEntry.objects.latest("id")` matches user / content type / change_message; (b) submit `title="forbidden"` → the error appears on the title input, save does not occur, `Book.objects.count()` unchanged; (c) edit an existing `Book`, change `summary`, save → `LogEntry` written with `construct_change_message`'s diff; (d) `readonly_fields` set on `AuthorAdmin` for `born` → the rendered widget refuses input, save preserves the old value.

**Checkpoint**: User Stories 1 + 2 work independently. CRUD-without-delete is shippable.

---

## Phase 5: User Story 3 — Operator deletes records and runs admin actions (Priority: P3)

**Goal**: Multi-row selection, action dispatch, message capture, delete path,
audit parity for actions and deletions, AND robust handling of actions that
raise mid-run (FR-019).

**Independent Test**: Multi-select 3 `Book` rows; run `mark_featured_action`;
assert `Book.objects.filter(featured=True).count()` grew by 3, the action's
`message_user(...)` notification ("3 books were updated") appears in the TUI,
and a `LogEntry` is written for each row (FR-017 / FR-018, SC-004). Run an
action that raises an exception; assert the TUI surfaces the error, **no
`LogEntry` is written claiming success**, and the operator is left on a
recoverable screen state (FR-019). Run the admin's built-in `delete_selected`
action on 2 rows; assert deletion + `log_deletion` entries (FR-016). Attempt
the same action as a user without `delete` permission; assert it's hidden
(FR-017's permission gate).

### Implementation for User Story 3

- [ ] T062 [US3] Write `admin_tui/core/actions.py` exposing `_get_actions(model_admin, request) -> dict[str, tuple[Callable, str, str]]` (delegates to `model_admin.get_actions(request)`) and `_run_action(model_admin, request, action_name, queryset) -> ActionResult` where `ActionResult` is a small `@dataclass(frozen=True)` with fields `messages: list[tuple[int, str, str]]`, `exception: BaseException | None`, and `partial_result: Any`. Control flow MUST be: (1) fire `overlay.before_action(request, action, queryset)`; (2) **wrap the call to `func(model_admin, request, queryset)` in `try/except Exception as exc`**; (3) read `request._messages.captured` for any messages emitted before the exception (some actions message-then-fail by design); (4) **only on the no-exception branch**, fire `overlay.after_action(request, action, queryset, result=partial_result)` and return `ActionResult(messages=..., exception=None, partial_result=...)`; (5) **on the exception branch**, do NOT fire `after_action`'s success path, do NOT route through the audit helpers in T058 (no `LogEntry` for failed work — FR-019), and return `ActionResult(messages=..., exception=exc, partial_result=None)` for the screen to surface. Re-raise only `KeyboardInterrupt` / `SystemExit`. Per `research.md` § R6 and spec FR-019.
- [ ] T063 [US3] Write `admin_tui/screens/action_confirm.py` defining `ActionConfirmScreen(Screen)` showing: the action description, the selected count + first 5 object reprs ("Confirm running 'Mark featured' on 3 Book records?"), and Yes / No bindings. On Yes: call `_run_action(...)`; if `result.exception` is None, push each `result.messages` entry as a Textual `notify(...)` (level mapped: INFO/SUCCESS/WARNING/ERROR) and return to the changelist; if `result.exception` is set, push messages PLUS one error `notify(..., severity="error")` summarising the exception type + first line of the traceback, leave the operator on `ActionConfirmScreen` with the failed action's button restored to a "Back" affordance (FR-019 recoverable state).
- [ ] T064 [US3] Extend `admin_tui/screens/changelist.py` adding multi-select (Space toggles the row's selection; selection set persisted in screen state across pagination), an actions picker (`x` opens a Textual `Select` populated by `_get_actions(...)` filtered to permitted actions), and dispatch to `ActionConfirmScreen`. Depends on T062, T063.
- [ ] T065 [US3] Extend `admin_tui/screens/changelist.py` (delete affordance): if `_check("delete", model_admin, request)` is True, surface the built-in `delete_selected` action; on confirm route through `model_admin.delete_queryset(request, queryset)` then `_log_deletion` per surviving object (call BEFORE delete to capture `object_repr`). If False, hide it from the action picker entirely (US3 acceptance scenario 2).
- [ ] T066 [US3] In `admin_tui/options.py` ensure `TuiAdmin.before_action(self, request, action, queryset)` and `after_action(self, request, action, queryset, *, result=None)` exist as no-op default hooks (already declared by T024; this task verifies their signatures match `contracts/public-api.md` and that they fire before/after `_run_action`'s body per T062's control-flow rules — in particular that `after_action` is NOT fired on the exception branch).

### Tests for User Story 3

- [ ] T067 [P] [US3] Write `tests/integration/sample_project/test_actions.py` (FR-017 — 019, SC-004): (a) multi-select 3 books, run `mark_featured_action` → 3 books marked, the message_user notification surfaces in the TUI via `pilot.app.query(Toast)` (or however captured messages display), and 3 `LogEntry` rows written; (b) **FR-019 error path** — define a sample action `failing_action(modeladmin, request, queryset)` in `sample_project/library/admin.py` that calls `modeladmin.message_user(request, "starting…")` then `raise RuntimeError("boom")`; assert the TUI captures the "starting…" message AND surfaces the error notification, **and** asserts `LogEntry.objects.filter(...).count()` is unchanged from before the action, **and** asserts `overlay.after_action` was NOT called (use a spy / `mock.patch.object`); (c) a user without `add` permission can still run actions that don't mutate, but `mark_featured_action` (which requires change) is filtered out by `get_actions(request)` for a view-only user.
- [ ] T068 [P] [US3] Extend `tests/integration/sample_project/test_crud.py` (FR-016): (a) selecting 2 rows and confirming delete → 2 `LogEntry` rows of type "deletion", correct content type and object_repr, rows actually deleted; (b) a `view`-only user has no delete affordance and `_check("delete", ...)` returns False; programmatic call to the same path raises `PermissionDenied`.

**Checkpoint**: Full CRUD + admin actions work, including the error path. Operator-facing v1 functionality is complete.

---

## Phase 6: User Story 4 — Developer extends the TUI (Priority: P3)

**Goal**: Exercise the **full** public extension surface (FR-024 lists 7 classes
of extension points) end-to-end from real overlays in the sample project, and
prove the surface is frozen at the 6 public names. This phase produces no
`admin_tui/` code beyond minor wiring; almost everything moves into
`sample_project/library/` to act as both regression tests and living
documentation (Constitution VIII).

**Independent Test**: With the sample project's overlay files in place, launch
the TUI; (a) the row action declared in the overlay appears in the actions
list; (b) the bulk action declared in the overlay also appears and operates
on a multi-row selection; (c) the key binding works; (d) the custom
`ColorField` renders with `ColorPickerWidget` on detail; (e) per-cell
`render_cell` override is visible on the changelist; (f) the `AuthorStatsScreen`
returned by `get_detail_screen` is what shows when an `Author` row is opened
(instead of the default `ChangeScreen`); (g) the `after_save` lifecycle hook
on `BookTui` fires (observable via a captured side-channel log line) when a
`Book` is saved. With every overlay file removed, every model still renders
and operates (FR-021 zero-config). Public-API surface test (T044) still
passes (FR-030).

### Implementation for User Story 4 (sample-project extension fixture)

- [ ] T069 [P] [US4] Write `sample_project/library/fields.py` defining `ColorField(models.CharField)` storing `"#RRGGBB"` strings (max_length=7, default `"#000000"`); override `formfield()` to return a `forms.CharField` with `RegexValidator(r"^#[0-9A-Fa-f]{6}$")`. Add a `color: ColorField` field to `Book` in `sample_project/library/models.py`. Generate and commit migrations (`uv run python sample_project/manage.py makemigrations library`).
- [ ] T070 [P] [US4] Write `sample_project/library/tui_widgets.py` defining `ColorPickerWidget(textual.widget.Widget)` — a small Textual widget with `compose()` yielding a `Static` color swatch + an `Input` for hex code; `on_input_changed` validates and updates the swatch. Pure Textual primitives, no admin_tui wrapping (Constitution VI). Depends on T069.
- [ ] T071 [US4] Write `sample_project/library/tui.py`: (a) `from admin_tui import register, TuiAdmin, field_widgets`; (b) `field_widgets.register(ColorField, lambda bound: ColorPickerWidget(value=bound.value()))`; (c) `@register(Book) class BookTui(TuiAdmin)` with `row_actions = ["mark_featured_via_tui"]`, `bulk_actions = ["bulk_recolor"]`, `key_bindings = [("f", "mark_featured_via_tui", "Feature")]`, a `render_cell(self, request, obj, field)` override that bolds the title in yellow when `obj.featured` (matching the quickstart example), a `mark_featured_via_tui(self, request, obj)` method that gates on `has_change_permission`, sets `obj.featured = True`, saves, and calls `_log_change`, AND a TUI-native bulk action `bulk_recolor(self, request, queryset)` that sets `color = "#FF8800"` on the queryset and emits a `message_user` line — exercises the `bulk_actions` extension slot from FR-024. Also overrides `after_save(self, request, obj, *, created)` to append a one-line entry to `BookTui._after_save_calls` (a class-level list used by tests T074 to assert the hook fired) — exercises the lifecycle-hook extension slot from FR-024. Depends on T069, T070, T034.
- [ ] T072 [P] [US4] In `admin_tui/sites.py` (already created in T023) verify `register_screen(slug, screen_cls)` exists per `data-model.md` § 2 and `contracts/public-api.md` § 3. Wire `AdminTuiApp` to consult `tui_site._screens` for a global tool screen reachable from the index (binding `g <slug>`). This makes the global-tool-screens extension point exercisable.
- [ ] T073 [P] [US4] In `sample_project/library/tui.py` register one global tool screen via `tui_site.register_screen("logs", LogEntryScreen)` where `LogEntryScreen` displays recent `LogEntry` rows for the session user. Also defines a `LogEntryScreen` class in `sample_project/library/screens.py` (separate file).
- [ ] T074 [US4] In `sample_project/library/screens.py` (the same file as T073), define `AuthorStatsScreen(textual.screen.Screen)` — a custom detail screen that shows the Author's name, book count (`obj.book_set.count()`), and most-recent-book title, with bindings `e` (jump to the default edit screen) and `q` (back). Then in `sample_project/library/tui.py`, register `@register(Author) class AuthorTui(TuiAdmin)` overriding `get_detail_screen(self, request, obj=None)` to return `AuthorStatsScreen`. This exercises the **full-screen replacement** extension slot from FR-024. Depends on T073.
- [ ] T075 [P] [US4] Add `BookForm.full_clean`-time `before_save` demonstration: in `sample_project/library/tui.py`'s `BookTui`, override `before_save(self, request, obj, *, created)` to populate `obj.normalised_title = obj.title.strip().lower()` (add `normalised_title: CharField(max_length=255, blank=True)` to `Book` in `sample_project/library/models.py` + a migration). This exercises the **before_save** lifecycle hook in FR-024 in a way the test in T077 can assert about — namely that the field is populated even when overlays don't explicitly set it on the form.

### Tests for User Story 4

- [ ] T076 [P] [US4] Write `tests/integration/sample_project/test_overlay.py` (FR-020 — 024, SC-005, Constitution VIII) asserting end-to-end coverage of every FR-024 extension class with the overlays from T071, T073, T074, T075 loaded: (a) row-action menu for a Book row contains `mark_featured_via_tui`; pressing `f` fires it; (b) bulk-action menu for a multi-row Book selection contains `bulk_recolor`; running it sets `color="#FF8800"` on selected rows and emits a `message_user` line; (c) `render_cell` override produces the bolded markup (assert by inspecting the `DataTable` cell content); (d) `ColorField` renders via `ColorPickerWidget` on the detail form; (e) opening an Author row shows `AuthorStatsScreen`, NOT the default `ChangeScreen`; (f) saving a Book via the create/edit form populates `normalised_title` (proves `before_save` fires) AND appends to `BookTui._after_save_calls` (proves `after_save` fires); (g) global tool screen `logs` is reachable via the `g logs` binding from the index and displays `LogEntry` rows; (h) **temporarily un-register every overlay via `tui_site.unregister(Book); tui_site.unregister(Author)`** and reload — both models still render fully with synthesized defaults (FR-021); (i) public API surface remains exactly the 6 names (re-import `admin_tui` and re-run T044's assertion).
- [ ] T077 [P] [US4] Write `tests/integration/sample_project/test_lifecycle_hooks.py` focusing specifically on the lifecycle-hook contract from FR-024 in isolation from T076's end-to-end test: (a) `before_save` fires exactly once per save and receives `created=True` on add / `False` on edit; (b) `after_save` fires after `_log_addition` / `_log_change` (assert ordering by `LogEntry.objects.count()` snapshot before/after the hook); (c) `before_action` fires before `func(...)` and `after_action` fires after, with `after_action` receiving the captured messages in `result`; (d) on action exception, `after_action` is NOT called (already tested in T067(b) but asserted here at the hook-contract level rather than the FR-019 level).

**Checkpoint**: All seven FR-024 extension classes (row actions, bulk actions,
key bindings, per-cell render override, per-model widget overrides, full-screen
replacement, lifecycle hooks) are exercised by sample-project overlays and
covered by passing tests. Public API surface is frozen and validated.
Constitution VIII fully satisfied — every extension point the spec promises
is demonstrated and regression-tested.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Concerns that affect multiple stories — inlines (R15), compat
warnings (R16), performance proof (SC-002), the Constitution-VII verification
test, the SC-005 release-candidate gate, documentation, and the wheel
build that produces the shippable artifact.

- [ ] T078 [P] Write `admin_tui/_internal/compat.py` exposing `scan(admin_site) -> dict[Model, list[str]]` that walks `admin_site._registry` and detects overrides of `change_view`, `add_view`, `delete_view`, `get_urls`, `change_form_template`, `change_list_template`, `Media`, and other surface-overriding attributes. Returns `{Model: [override_name, ...]}`. In `IndexScreen.on_mount` (T050), surface ONE `notify(...)` per model the first time it's accessed in this session when `_loaded["COMPAT_WARNINGS"]` is True. Per `research.md` § R16.
- [ ] T079 Extend `admin_tui/core/forms.py` and `admin_tui/screens/change.py` to support inlines via `model_admin.get_inline_instances(request, obj)`: each inline renders as a Textual `DataTable` editable region beneath the main fieldsets, with its own formset-backed widget rendering. Per `research.md` § R15 and FR-024. This is the most complex form path; isolate to this phase per the phased roadmap.
- [ ] T080 [P] Write `tests/integration/sample_project/test_inlines.py`: add an inline relation in `sample_project/library/models.py` (`BookChapter(book: FK->Book, title, ordering)` with `BookChapterInline(admin.TabularInline)`); assert that the inline appears beneath the `Book` detail form, that adding / editing / deleting rows produces the same `LogEntry` change message the web admin would produce, and that `has_*_permission` on the inline model is honored. Migrations included.
- [ ] T081 [P] Write `tests/integration/sample_project/test_performance.py` (SC-002): seed 100,000 `Book` rows via a `pytest` fixture using bulk-create; assert that opening the changelist and pressing PgDn 10 times completes in under 3 seconds total (p95 ~300 ms / transition target). Memory: assert `tracemalloc.get_traced_memory()[1]` stays bounded by `PAGE_SIZE`-relative limits, not by the row count. Mark `@pytest.mark.slow`; CI runs the slow set in a separate job to keep the default suite fast.
- [ ] T082 [P] Write `tests/unit/test_no_network.py` asserting Constitution VII: during a full `async with AdminTuiApp(session=...).run_test()` driving every default screen, no `socket.socket(...).bind(...)` or `.connect(...)` call is made except to the SQLite database (or, more strictly, monkeypatch `socket.socket` to raise `AssertionError` and assert the test still passes — proves the runtime imports + flow never touch the network stack). LOW-frequency regression catcher: if a future contributor adds a metrics ping or remote-update check, this test fires.
- [ ] T083 [P] Write `docs/release-checklist.md` codifying the SC-005 gate: a release-candidate item that times a fresh contributor following `docs/quickstart.md` § 4–6 end-to-end, expects ≤30 minutes from `pip install` to a working overlay in their own project, and records the run in the RC notes. Reference the resulting figure in each release announcement.
- [ ] T084 [P] Write `docs/architecture.md` containing: one diagram (the object-graph from `data-model.md`), the synthetic-request explainer (lift from `research.md` § R3), and a one-paragraph reading guide pointing at the contracts files.
- [ ] T085 [P] Write `docs/quickstart.md` as the operator-facing quickstart. Source of truth is `specs/001-admin-tui-mvp/quickstart.md`; either copy it verbatim into `docs/quickstart.md` or, preferably, make `docs/quickstart.md` a one-line pointer at the spec file so they cannot drift.
- [ ] T086 [P] Write `README.md` at the repo root: name + tagline; a "Trust model" callout BEFORE install instructions (per FR-005 and Constitution VII); install (`uv add <name>` / `pip install <name>`); 30-second quickstart pointing at `docs/quickstart.md`; supported Python / Django matrix; a "Stability" section pointing at `contracts/public-api.md`; link to the constitution.
- [ ] T087 Run a final wheel build: `uv build`; inspect `dist/*.whl` to verify it is platform-agnostic and excludes `sample_project/` and `tests/`; install the wheel into a fresh `uv` env and smoke-launch `manage.py admin_tui` against a one-line Django project that has only `django.contrib.admin` + a trivial registered model. The TUI MUST boot to a working index. Depends on every preceding task that touches `admin_tui/`.
- [ ] T088 [P] Verify the CI matrix is green for every supported (Python × Django) cell: 3.12 × 4.2, 3.12 × 5.2, 3.12 × 6.0, 3.13 × 5.2, 3.13 × 6.0, 3.14 × 6.0. Surface any failing cell as a blocker — do not paper over with `xfail`.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: T001 must complete first; everything else parallelizable except T007 (uv sync) which depends on T005 (pyproject.toml).
- **Foundational (Phase 2)**: Depends on Phase 1 fully complete. **BLOCKS all user stories.** Within Phase 2, the dependency chain is roughly: messages (T017) → request (T018) → permissions (T019) → site/options (T023, T024) → app (T035) → CLI (T037); widget registry (T026 — T034) is an independent chain in parallel; sample-project (T038 — T043) is a parallel chain.
- **User Stories (Phase 3+)**: All depend on Foundational completion. Independent of each other:
  - US1 (T049 — T056) — MVP path
  - US2 (T057 — T061) — independent of US1's screen code except for extending `change.py`
  - US3 (T062 — T068) — independent except for extending `changelist.py` (multi-select adds to US1's screen)
  - US4 (T069 — T077) — independent; lives in sample_project + a small `admin_tui/sites.py` wiring task (T072)
- **Polish (Phase 7)**: Inlines (T079, T080) depend on US2's form path. Compat warnings (T078) depend on the index screen (US1's T050). Performance (T081) depends on US1. The no-network test (T082) depends on every default screen existing (US1–US3). Docs and packaging (T083 — T088) depend on all stories.

### User Story Dependencies

- US1 → none (MVP).
- US2 → none structurally, but extends `admin_tui/screens/change.py` which US1 created. If US1 and US2 are worked in parallel, US2's edits to `change.py` must merge cleanly with US1's read-only base.
- US3 → none structurally; extends `admin_tui/screens/changelist.py` from US1 (multi-select). Same merge consideration.
- US4 → none; all work is additive in `sample_project/library/` + non-conflicting reads/wiring in `admin_tui/sites.py` (T072).

### Within Each User Story

- Models in `sample_project` before services in `admin_tui/core/` that reference them.
- Tests can be written in parallel with implementation but MUST be authored against the contracts in `specs/001-admin-tui-mvp/contracts/`, not against the live implementation, to keep them honest.

### Parallel Opportunities

- All [P] tasks in Setup can run in parallel.
- Within Foundational: widget defaults (T027 — T033) are 7-way parallel; sample-project files (T038 — T042) are 5-way parallel; foundational tests (T044 — T048) are 5-way parallel.
- User Stories run in parallel once Foundational completes.
- Within Polish: T080 / T081 / T082 / T083 / T084 / T085 / T086 / T088 are all parallel; T087 (wheel build) sequences last.

---

## Parallel Example: User Story 1

```bash
# After Foundational checkpoint:
Task: T049 admin_tui/screens/__init__.py
Task: T055 tests/integration/sample_project/test_index.py
Task: T056 tests/integration/sample_project/test_changelist.py

# Implementation sequence (sequential because they edit the same files):
T050 IndexScreen → T051 core/changelist.py → T052 ChangelistScreen → T053 ChangeScreen → T054 App routing wire-up
```

## Parallel Example: User Story 4

```bash
# All sample-project additions can be written in parallel:
Task: T069 sample_project/library/fields.py (+ migration)
Task: T070 sample_project/library/tui_widgets.py
Task: T072 admin_tui/sites.py wiring for register_screen + AdminTuiApp `g <slug>` binding
Task: T075 sample_project/library/models.py adds normalised_title (+ migration)

# Then sequentially:
T071 sample_project/library/tui.py (depends on T069 + T070 + T075)
T073 register the global tool screen LogEntryScreen
T074 AuthorStatsScreen + AuthorTui.get_detail_screen override
T076 + T077 the test suites for the overlay + lifecycle hooks
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (~13 tasks, mostly parallel).
2. Complete Phase 2: Foundational (~35 tasks, heavily parallelizable).
3. Complete Phase 3: User Story 1 (8 tasks).
4. **STOP and VALIDATE**: launch the TUI against `sample_project`, exercise
   the SC-001 + SC-003 paths manually, run `tests/integration/sample_project/`.
5. If green: tag as `v0.1.0-mvp-readonly` and demo. The MVP is a usable
   read-only admin browser at this point — already worth shipping internally.

### Incremental Delivery

1. MVP (US1) → demo → tag `v0.1.0`.
2. Add US2 (create/edit) → tag `v0.2.0`.
3. Add US3 (delete + actions, including FR-019 error path) → tag `v0.3.0`.
4. Add US4 (sample-project extension fixture covering every FR-024 slot)
   → tag `v0.4.0`.
5. Polish (inlines, perf, no-network test, RC gate, docs, packaging) → tag
   `v1.0.0` and publish.

Each tag is a milestone the spec's Success Criteria can be re-checked
against:

- `v0.1.0` validates SC-002 (initial), SC-003, SC-007.
- `v0.2.0` adds SC-004 (the audit-parity gate).
- `v0.3.0` completes SC-001 and SC-004 across all CRUD + action paths,
  including FR-019.
- `v0.4.0` validates SC-005 (the 30-min extension story) and locks
  SC-006 (the 6-name public-surface freeze).
- `v1.0.0` adds the SC-002 100k-row proof, the Constitution-VII no-network
  test, and the wheel-install proof.

### Parallel Team Strategy

With three developers post-Foundational:

1. All three on Phase 1 + Phase 2 (~48 tasks) until checkpoint.
2. Then:
   - **Dev A** — US1 (screens + changelist core).
   - **Dev B** — US2 + US3 (extending `change.py` and `changelist.py` —
     same files as A's work; coordinate via the file-level dependency
     graph above, or sequence US2/US3 behind US1).
   - **Dev C** — US4 (sample-project extension; mostly disjoint from
     A and B).
3. Polish phase parallelises across all three for inlines / perf /
   no-network test / docs / packaging.

---

## Notes

- [P] tasks = different files, no incomplete-task dependencies.
- [Story] label maps task → user story for traceability.
- Each user story is independently completable and testable per spec.md
  § "Independent Test" for that story.
- Per Constitution I ("Reuse Django's admin; never reimplement it"), every
  task that touches admin behavior MUST call through the methods listed in
  `contracts/internal-django-surface.md`. CI's lint step rejects PRs that
  reimplement filtering, validation, or permission logic Django provides.
- Per Constitution V ("Small, intentional, stable public API"), every
  task that adds a name to `admin_tui.__all__` requires a justification in
  the PR description, a test in `tests/unit/test_public_api.py`, and a
  docs entry in `contracts/public-api.md`. The current public surface is
  frozen at the 6 names listed in T014.
- Per Constitution VIII ("Every extension point covered by the sample
  app"), the sample project in `sample_project/library/` exercises every
  class of extension point FR-024 enumerates — row actions, bulk actions,
  key bindings, per-cell rendering, per-model widget overrides, full-screen
  replacement, and lifecycle hooks. Removing any of T071 / T073 / T074 /
  T075 / T076 / T077 weakens that gate; do not delete them silently.
- Commit after each task or logical group; the git extension's
  `after_implement` auto-commit hook is opt-in.
- Stop at any checkpoint to validate the increment independently.
- Avoid: vague tasks (replace with concrete file paths), cross-story
  dependencies that break independent delivery, premature additions to
  the public surface.
