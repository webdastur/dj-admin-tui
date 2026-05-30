---

description: "Task list for Django Admin TUI v2 — UI redesign & Django parity"
---

# Tasks: Django Admin TUI — UI Redesign & Django Parity (v2)

**Input**: Design documents from `specs/002-ui-redesign-django-parity/`

**Prerequisites**: `plan.md`, `spec.md` (+ `## Clarifications`), `research.md` (D1–D10),
`data-model.md`, `contracts/{settings,interaction,theming}.md`, `quickstart.md`.

**Tests are INCLUDED**. The spec's `Measurable Outcomes` (SC-001..SC-007) and Constitution
Principle VIII ("an untested extension point is an undocumented, unkept promise") mandate
automated coverage. Several requirements are *defined by* their tests: SC-001 (layout
stability), FR-013 (a regression test that fails pre-fix), SC-002/006 (mouse vs keyboard
parity), SC-004/005 (theming). Test tasks therefore lead each story.

**Organization**: Grouped by user story so each is independently implementable and
testable. Phases run in spec priority order: **US1 (P1, MVP) → US3 (P1) → US2 (P2) →
US4 (P3)**.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks).
- **[Story]**: US1 / US2 / US3 / US4. Setup, Foundational, and Polish carry no label.
- Every task names the exact file path it touches.

## Path Conventions

Per `plan.md` § Project Structure (v2 touch map):

- Package source: `admin_tui/...` (new internal modules: `themes/`, `widgets/layout.py`,
  `widgets/filters.py`; edited screens under `admin_tui/screens/`).
- Sample project: `sample_project/...`
- Tests: `tests/unit/...` and `tests/integration/sample_project/...`
- Docs: `docs/...`

**Invariant for every phase (SC-007)**: no change may alter v1 data behavior. The full v1
test suite MUST stay green throughout; treat a v1 regression as a v2 bug.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the new internal module skeletons and confirm the v1 baseline is green
before touching anything.

- [X] T001 Confirm the v1 baseline is green: run `uv run pytest -q` and record that all v1 tests pass; this is the SC-007 reference point. Do not proceed if v1 is already red.
- [X] T002 [P] Create internal module skeletons with docstrings + typed stubs: `admin_tui/widgets/layout.py` (`compute_column_widths`, `truncate_cell`), `admin_tui/widgets/filters.py` (`FilterSidebar`), `admin_tui/themes/__init__.py` (`register_bundled_themes`, theme-name constants) and `admin_tui/themes/django.py` (palette `Theme` factory). Stubs only — `raise NotImplementedError` / empty — so later phases fill them.
- [X] T003 [P] Add empty test files so suites are discoverable: `tests/unit/test_layout.py`, `tests/unit/test_appearance_conf.py`, `tests/integration/sample_project/test_changelist_layout.py`, `tests/integration/sample_project/test_mouse.py`, `tests/integration/sample_project/test_save_matrix.py`, `tests/integration/sample_project/test_theming.py` (each with a `pytest.mark` import and a `pass` placeholder).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Sample-project data shared by every story — a wide-text column (US1
truncation), `list_filter` (US1 filter sidebar / US2 mouse), and a full-default-widget
model incl. M2M (US3 save matrix). No story can be meaningfully tested without these.

**⚠️ CRITICAL**: Complete before starting any user story.

- [X] T004 [P] Extend `sample_project/library/models.py`: add a model `Showcase` (or extend an existing one) whose fields cover the full default-widget set — `CharField`, `TextField` (long values for truncation), `BooleanField` + a nullable `BooleanField(null=True)`, a `choices=` field, `ForeignKey`, `ManyToManyField`, `DateField`, `DateTimeField`, `JSONField`, `IntegerField`, `DecimalField`, with `null=True`/`blank=True` variants. Keep `__str__` meaningful.
- [X] T005 Update `sample_project/library/admin.py`: register the new model with a `ModelAdmin` that declares `list_display` including at least one intentionally long column, `list_filter` (a boolean + the choices field + the FK), `search_fields`, and the full field set in `fieldsets` (so US3 can drive every widget). Keep existing `Book`/`Author`/`Tag` admins intact.
- [X] T006 Generate and commit the migration for T004: `uv run python sample_project/manage.py makemigrations library` → `sample_project/library/migrations/000X_*.py`. Verify `migrate` runs clean on a fresh `db.sqlite3`.
- [X] T007 [P] Add a small fixture/factory helper in `tests/integration/sample_project/conftest.py` (or extend the existing conftest) that creates `Showcase` rows with long text values and related FK/M2M targets, reused by the layout, mouse, and save-matrix suites.

**Checkpoint**: Sample project exercises wide columns, filters, and every default widget.

---

## Phase 3: User Story 1 — Stable, Django-like changelist (Priority: P1) 🎯 MVP

**Goal**: The changelist renders fixed-width truncated columns that never reflow on
selection, shows the focused cell's full value in a footer bar, exposes a filter sidebar
and pagination controls, and carries Django-admin changelist furniture (result count,
column headers, object-tools). Palette/theme colors come later (US4).

**Independent Test**: Navigate the sample `Showcase` changelist (whose cells overflow): every
column width and row height stays constant across cursor moves (SC-001); the footer shows
the focused cell's full value; selecting a filter entry yields the same result set as the
web admin for the same params (FR-004); a narrow terminal scrolls horizontally with no
dropped columns (FR-005).

### Tests for User Story 1 ⚠️ (write first, ensure they FAIL)

- [X] T008 [P] [US1] Unit tests in `tests/unit/test_layout.py` for `compute_column_widths` (output depends only on columns+page-rows+caps, never on a "selected" arg; respects MIN/MAX caps; selection column = 3) and `truncate_cell` (ellipsis on overflow; CJK/emoji double-width via `rich.cells.cell_len`; long single token still cut at boundary; strips control chars/newlines/tabs). Assert `cell_len(result) <= width` always.
- [X] T009 [P] [US1] Integration test in `tests/integration/sample_project/test_changelist_layout.py` using `Pilot`: capture column widths + row heights, move the cursor across all rows, assert they are unchanged (SC-001); assert the focused-cell footer preview updates and equals the untruncated value; assert selecting a `list_filter` entry produces the same `result_list` pks as Django's web admin for the same query params (FR-004); assert a narrow size horizontally scrolls and drops no columns (FR-005).

### Implementation for User Story 1

- [X] T010 [US1] Implement `compute_column_widths(columns, page_rows, caps)` and `truncate_cell(value, width)` in `admin_tui/widgets/layout.py` per research D1 / data-model ColumnSpec (pure functions; page-sampled; `rich.cells`-aware). (Makes T008 pass.)
- [X] T011 [US1] Implement `FilterSidebar` in `admin_tui/widgets/filters.py` from `changelist.get_filters(request)` → groups/entries with `display`/`selected`/`query_string` (data-model FilterPanelState; research D4). Selecting an entry merges its `query_string` into the screen's `query_params`. Keyboard-navigable; rendered only when `list_filter` is non-empty.
- [X] T012 [US1] Rework `admin_tui/screens/changelist.py` table render (`_refresh_table`): use `compute_column_widths` to `add_column(..., width=w)` and `truncate_cell` for every cell; remove reliance on DataTable content auto-sizing. Widths recomputed only in `_rebuild()` (search/filter/sort/page), never on cursor move (SC-001).
- [X] T013 [US1] Add the footer cell-preview bar to `admin_tui/screens/changelist.py`: a fixed 1-line `Static#cell-preview` docked above `Footer`; update it on `DataTable.RowHighlighted`/`CellHighlighted` from `overlay.render_cell(...).display` (research D2 / FR-003). Never resizes rows/columns.
- [X] T014 [US1] Mount the `FilterSidebar` in `admin_tui/screens/changelist.py` (right-docked) and wire entry-selection → `query_params` merge → `_reset_request_and_rebuild()`. Show only when the model declares `list_filter`.
- [X] T015 [US1] Add the changelist furniture to `admin_tui/screens/changelist.py`: a header/title + breadcrumb line (`Home › App › Model`), an object-tools row with an `[+ Add]` `Button` (gated by `has_add_permission`, mirrors the `a` binding), and a pagination region (`[‹ Prev]`, `page N / M`, `[Next ›]` `Button`s mirroring PgUp/PgDn) — research D5/D7, FR-004. Structure only; colors arrive in US4.
- [X] T016 [US1] Update keyboard open-detail path in `admin_tui/screens/changelist.py`: keep `Enter` → `action_open_detail`; stop auto-opening from `on_data_table_row_selected` (so a future single mouse click won't open — prepares US2). Verify keyboard browse still matches v1.

**Checkpoint**: Changelist is stable, truncated, filterable, paginated, and Django-shaped — fully usable by keyboard.

---

## Phase 4: User Story 3 — Create/edit saves for every default field type (Priority: P1)

**Goal**: Every default widget/field type saves correctly on create and edit, including the
currently-broken multi-value (M2M) and split (MultiWidget) cases; each fix is locked by a
regression test.

**Independent Test**: The save matrix creates and edits a `Showcase` row touching every
field type; each save succeeds, persisted values match input, validation errors land on the
right field, and the `LogEntry` matches the web admin. The previously-failing cases fail on
pre-fix code and pass after (FR-013).

### Tests for User Story 3 ⚠️ (write first, ensure the broken cases FAIL)

- [X] T017 [P] [US3] Save-matrix integration tests in `tests/integration/sample_project/test_save_matrix.py` using `Pilot`: parametrize over each field type (text, boolean, nullable boolean, choice, FK, **M2M**, date, datetime, JSON, integer, decimal, null/blank). For each: drive create + edit, assert save succeeds, persisted value == input, and `LogEntry` (user/action flag/content type/change message) matches the web admin. Run against current code first and record which cases fail (D8).

### Implementation for User Story 3

- [X] T018 [P] [US3] Add a default M2M renderer `admin_tui/widgets/defaults/many_to_many.py` (e.g. a Textual `SelectionList`) for `ManyToManyField`/`ModelMultipleChoiceField`, and register it in `admin_tui/widgets/registry.py` (or `widgets/defaults/__init__.py`) walking the field MRO like the other defaults.
- [X] T019 [US3] Fix `_read_widget_value` in `admin_tui/screens/change.py` to return a **list of pks** for multi-value widgets (SelectionList / SelectMultiple) and to handle MultiWidget sub-values, per research D8 / data-model SaveData. Keep the existing Input/Switch/Select/TextArea handling.
- [X] T020 [US3] Fix `_gather_data` in `admin_tui/screens/change.py` so multi-value/MultiWidget fields are included in the data dict (not dropped), using keys Django's widgets expect via `value_from_datadict`. Ensure unchecked boolean → absent/False semantics.
- [X] T021 [US3] Verify/fix the edit rebind in `admin_tui/screens/change.py` `action_save`: `_build_form(..., obj=self.obj, data=data)` must bind `instance=obj` so a save **updates** rather than inserts; confirm `save_related` persists M2M. Keep the v1 `save_model → save_related → construct_change_message → log_addition/log_change` sequence unchanged (Constitution I/II, FR-014).

**Checkpoint**: All default field types save correctly; the matrix is green and guards against regression.

---

## Phase 5: User Story 2 — Full mouse support (Priority: P2)

**Goal**: The whole TUI is mouse-drivable — single-click focus, double-click open,
checkbox-column multi-select, header-click sort, clickable filters/pagination/object-tools,
wheel scroll — with every target keeping its keyboard equivalent.

**Independent Test**: Complete the full workflow (index → changelist → multi-select → run
action / open record → edit → save → return) using only mouse events, and again using only
keyboard events; both reach the same end state and produce identical audit entries
(SC-002). With mouse reporting disabled, keyboard-only still completes (SC-006).

### Tests for User Story 2 ⚠️ (write first)

- [X] T022 [P] [US2] Mouse/keyboard parity tests in `tests/integration/sample_project/test_mouse.py` using `Pilot.click`/`Pilot.hover`/double-click + key presses: assert the mouse-only and keyboard-only runs of the full workflow reach the same end state and produce identical `LogEntry` rows (SC-002); assert a single click only focuses (does not open), a double-click opens, a checkbox-cell click toggles selection, a header click sorts, a filter-entry click filters, wheel scroll does not change selection (FR-008/008a/009/011); assert keyboard-only completion (SC-006).

### Implementation for User Story 2

- [X] T023 [US2] In `admin_tui/screens/changelist.py`, implement the click model (research D3): `on_click` with `event.chain == 2` over the table body → `action_open_detail` (double-click); single click leaves DataTable's default focus move (updates the footer preview from US1). Ensure single click never opens.
- [X] T024 [US2] In `admin_tui/screens/changelist.py`, handle a click on the selection checkbox column cell (resolve the clicked cell key == `SELECTION_COLUMN_KEY`) → toggle that row in `selected_pks` (mouse path for the `Space` binding); render a ☐/☑ header glyph.
- [X] T025 [US2] In `admin_tui/screens/changelist.py`, handle `DataTable.HeaderSelected` → run the same sort cycle as `action_cycle_sort` for the clicked column (skip the selection column). Make filter entries (US1 `FilterSidebar`) and the pagination/`+ Add` buttons (US1) respond to clicks — verify they invoke the same handlers as their key bindings.
- [X] T026 [P] [US2] In `admin_tui/screens/index.py`, make app-section and model rows clickable (single click navigates, mirroring `Enter`); keep the Django-look header/breadcrumb.
- [X] T027 [P] [US2] In `admin_tui/screens/change.py` and `admin_tui/screens/action_confirm.py`, confirm fields focus on click and Save/Cancel/action buttons respond to clicks (Textual `Button`s already do — add a click→focus path for field widgets where needed and a test hook). No keyboard binding is removed.

**Checkpoint**: Every workflow is completable by mouse and by keyboard; parity tests pass.

---

## Phase 6: User Story 4 — Settings-driven theming + Django palette (Priority: P3)

**Goal**: A bundled `django` theme (the admin's blue/grey palette) is the default look;
`THEME_NAME` selects among bundled/registered themes; the existing `.tcss` `THEME` overrides
on top. Appearance never affects data behavior.

**Independent Test**: With no appearance config the TUI uses the `django` theme; setting
`THEME_NAME` to another registered theme visibly changes presentation while result sets,
saves, and audit stay identical (SC-004); an invalid `THEME_NAME` fails at startup with a
clear `ImproperlyConfigured` naming the key (SC-005).

### Tests for User Story 4 ⚠️ (write first)

- [X] T028 [P] [US4] Unit tests in `tests/unit/test_appearance_conf.py`: `THEME_NAME` defaults to `"django"` when unset; a registered name validates; an unregistered name raises `ImproperlyConfigured` naming the key (FR-018/SC-005); precedence — a `.tcss` `THEME` plus a `THEME_NAME` both resolve (FR-015a).
- [X] T029 [P] [US4] Theming integration tests in `tests/integration/sample_project/test_theming.py` using `Pilot`: launching with `ADMIN_TUI={}` applies the `django` theme; switching `THEME_NAME` changes `app.theme` but yields identical `result_list` pks and identical save/`LogEntry` behavior (SC-004); an invalid `THEME_NAME` aborts launch before any screen (SC-005).

### Implementation for User Story 4

- [X] T030 [P] [US4] Implement the bundled themes in `admin_tui/themes/django.py` (a `textual.theme.Theme` mapping the Django admin palette — header green/blue, link blue, neutral greys — to Textual variables) and a neutral fallback re-exposed by name; implement `register_bundled_themes(app)` + name constants in `admin_tui/themes/__init__.py` (research D6, contracts/theming.md).
- [X] T031 [US4] Add the `THEME_NAME` key to `admin_tui/conf.py`: default `None`→`"django"`, validate against registered theme names at resolve time, raise `ImproperlyConfigured` on unknown (FR-018). Update `_DEFAULTS`/`_VALID_KEYS` and keep the existing `THEME` (`.tcss`) validation. (Makes T028 pass.)
- [X] T032 [US4] Wire theming in `admin_tui/app.py`: register bundled themes (add an overridable `on_register_themes` hook), resolve `THEME_NAME` → `self.theme`, and keep `CSS_PATH = THEME` layered on top (research D6 precedence). Carry `theme_name` on the `TuiSession` like `theme_path`.
- [X] T033 [US4] Add a `--theme-name` flag to `admin_tui/management/commands/admin_tui.py`, parallel to the existing `--theme`; it overrides the loaded value on the session only (contracts/settings.md reading order).
- [X] T034 [US4] Apply the Django-look palette across screens by referencing theme variables (`$primary`, `$surface`, `$accent`, …) in the `DEFAULT_CSS` of `admin_tui/screens/{index,changelist,change,action_confirm}.py` so the structural furniture built in US1 now reads as the Django admin (FR-006/006a). No hardcoded colors.

**Checkpoint**: Default look evokes the Django admin; theme is settings-selectable; data behavior unchanged.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Lock invariants, docs, and the sample-app/CI guarantees.

- [X] T035 Run the full v1 suite + all v2 suites: `uv run pytest -q`; confirm SC-007 (every v1 test still green) and all new suites pass.
- [X] T036 [P] Confirm the public-API surface test (`tests/unit/test_public_api.py`) still passes — v2 added **zero** new public Python names (only the `THEME_NAME` settings key). If it references settings keys, update its fixture to include `THEME_NAME`.
- [X] T037 [P] Update `docs/quickstart.md` and `docs/README.md` with the mouse map and theming-via-settings sections (sync with `specs/002-ui-redesign-django-parity/quickstart.md`); document that edits now save for all default field types.
- [X] T038 [P] Update `docs/architecture.md` (or add a note) describing the fixed-width/truncation layout, the footer preview, and the theme-layering model.
- [X] T039 Ensure CI (`.github/workflows/ci.yml`) runs the new suites across the Django/Python matrix (Constitution VIII — sample-app extension coverage); confirm the `Showcase`/filter/save-matrix/theming paths are exercised.
- [X] T040 [P] Run `uv run ruff check && uv run ruff format --check` and fix any lint/format issues introduced by v2 edits.
- [X] T041 Manually run `quickstart.md` (delta) end-to-end against the sample project: launch default (django theme), switch `--theme-name`, drive a full mouse workflow, and edit a `Showcase` row touching every field type.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies — start immediately.
- **Foundational (Phase 2)**: depends on Setup; **BLOCKS all user stories** (the sample
  data they test against).
- **User Stories (Phase 3–6)**: all depend on Foundational. In priority order US1 → US3 →
  US2 → US4. US2 (mouse) has a soft dependency on US1 (it reuses the stable table, footer
  preview, filter sidebar, and the "don't open on RowSelected" change from T016). US4 is
  independent of US1/US2/US3 except that T034 styles furniture built in US1.
- **Polish (Phase 7)**: depends on all desired stories.

### User Story Dependencies

- **US1 (P1)**: after Foundational. No dependency on other stories.
- **US3 (P1)**: after Foundational. Independent of US1 (touches `change.py`, not the
  changelist). Can run in parallel with US1.
- **US2 (P2)**: after Foundational; best after US1 (reuses the stable table + T016).
- **US4 (P3)**: after Foundational; T034 best after US1's furniture exists.

### Within Each User Story

- Tests are written first and MUST fail before implementation (esp. US3's save matrix —
  FR-013 requires a pre-fix failure).
- Helpers/widgets before the screens that use them (T010/T011 before T012–T015; T018 before
  T019–T021; T030/T031 before T032–T034).

### Parallel Opportunities

- Setup: T002, T003 in parallel.
- Foundational: T004, T007 in parallel (T005 depends on T004; T006 depends on T004/T005).
- US1 vs US3 can be developed in parallel (different files: changelist/layout/filters vs
  change.py/m2m widget).
- Within a story, `[P]` test tasks run together (T008+T009 build then run; T017; T022;
  T028+T029).
- US4 theme authoring (T030) parallels conf/app wiring prep.

---

## Parallel Example: User Story 1

```bash
# Write US1 tests together (they will fail until T010+):
Task: "Unit tests for compute_column_widths/truncate_cell in tests/unit/test_layout.py"
Task: "Integration layout-stability + filter test in tests/integration/sample_project/test_changelist_layout.py"

# Then build the helpers in parallel before wiring the screen:
Task: "Implement layout helpers in admin_tui/widgets/layout.py"
Task: "Implement FilterSidebar in admin_tui/widgets/filters.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 only)

1. Phase 1 Setup → 2. Phase 2 Foundational → 3. Phase 3 US1 → **STOP & VALIDATE**: the
   changelist glitch is gone (SC-001), filters/pagination work, keyboard browse matches v1.
   This alone resolves the headline complaint and is demoable.

### Incremental Delivery

1. Setup + Foundational → foundation ready.
2. US1 → the glitch fix (MVP). 3. US3 → edits save correctly (the other P1 "it's broken"
   report). 4. US2 → mouse. 5. US4 → Django palette + settings theming.
6. Each story is independently testable; SC-007 (v1 green) is checked after every phase.

### Parallel Team Strategy

After Foundational: Dev A → US1 (changelist/layout/filters), Dev B → US3 (change.py/m2m).
Then Dev A → US2 (builds on US1), Dev B/C → US4 (themes/conf/app). Integrate via the parity
and theming suites.

---

## Notes

- `[P]` = different files, no dependency on an incomplete task.
- `[Story]` maps each task to a spec user story for traceability.
- Every phase must keep the v1 suite green (SC-007) — verify at each checkpoint.
- US3's matrix MUST be run against pre-fix code to capture the real failures (FR-013).
- No new public Python name is permitted; the only public-surface addition is the
  `THEME_NAME` settings key (FR-031: justified + tested in T028/T029 + documented).
- Commit after each task or logical group.
