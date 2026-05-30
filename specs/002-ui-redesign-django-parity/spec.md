# Feature Specification: Django Admin TUI — UI Redesign & Django Parity (v2)

**Feature Branch**: `002-ui-redesign-django-parity`

**Created**: 2026-05-30

**Status**: Draft

**Input**: User description: "now core of the project is ready. We have to redesign
its UI — it should match the Django UI (nearest possible). UI right now is glitchy:
items get cropped, and when an item is selected it shows the full text, which is not
the desired way. We have to make the TUI identical to Django features. Also UI design
(optional) should be controlled through Django settings. The TUI should react to mouse
actions — we want to be able to work with the mouse, not only strictly with keybinds.
Some model edits are not working and should be fixed."

## Context

The v1 feature (`001-admin-tui-mvp`) delivered the functional core: a Textual TUI that
drives the Django admin (index, changelist, detail, create, edit, delete, actions) by
reusing `ModelAdmin` internals, honoring permissions and audit. v1 was correctness- and
extensibility-focused; presentation was minimal. This feature (v2) is a
**presentation, interaction, and bug-fix pass** on top of that working core. It does not
re-derive any admin behavior or change the public extension surface beyond what theming
and mouse interaction require; it makes the existing behavior look like the Django admin,
behave smoothly, respond to the mouse, and corrects edit paths that currently fail.

## Clarifications

### Session 2026-05-30

- Q: How is a truncated cell's full value revealed without reflowing the table? → A:
  Detail view is canonical; **plus** a non-reflowing peek of the focused cell's full
  value in a footer/status bar (no row resize, no layout shift).
- Q: What is the changelist mouse row-click model? → A: Single click highlights/focuses
  the row (mirrors keyboard move); double-click (or clicking an explicit open link) opens
  the detail; a separate selection checkbox/toggle column handles multi-select.
- Q: How does the changelist behave when the terminal is narrower than the columns? → A:
  Both — columns keep stable widths and truncate, and when their total exceeds the
  viewport the table scrolls horizontally (keyboard + mouse) so every declared column
  stays reachable; columns are never silently dropped.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Operator sees a stable, Django-like changelist with no layout glitches (Priority: P1) 🎯 MVP

An operator opens a model's changelist. Columns are laid out like the Django admin
changelist: a header row with column labels, fixed-width truncated cells, a selectable
row highlight, and a result count. Moving the selection up and down highlights rows
**without** changing their width, reflowing the table, or expanding the selected row to
show its full untruncated text. Long values stay truncated in the table (with a visible
truncation indicator); the operator sees the full value by opening the record's detail
view, with the focused cell's full value also shown in a fixed footer/status-bar preview
— never by the row expanding or the table reflowing on selection.

**Why this priority**: this is the headline complaint — the current selection behavior
(cropped cells that expand to full text on highlight) makes the table jump and feels
broken. A stable, predictable changelist is the foundation every other screen sits on,
and it is the strictest test of the new layout/truncation model.

**Independent Test**: against the in-repo sample project, navigating the changelist with
the keyboard and the mouse MUST keep every column at a stable width and every row at a
stable height across selection changes; no selected row may grow, reflow, or reveal text
that unselected rows hide. The visible result set and ordering MUST remain identical to
v1 (i.e. identical to the web admin's changelist for the same query).

**Acceptance Scenarios**:

1. **Given** a changelist whose cells contain values longer than the column width,
   **When** the operator moves the selection from one row to another, **Then** every
   column keeps the same width, every row keeps the same height, and the only visible
   change is the row highlight — no cell expands to show its full text.
2. **Given** a truncated cell value, **When** the operator wants the full value, **Then**
   it is available by opening the record's detail view, and the focused cell's full value
   is also shown in a fixed footer/status-bar preview — neither path resizes the row or
   shifts the table layout.
3. **Given** a terminal narrower than the sum of column widths, **When** the operator
   views the changelist, **Then** columns keep their stable widths (content truncated) and
   the table scrolls horizontally so every declared column stays reachable; no column is
   dropped and the layout never breaks or crashes (continuing the v1 edge-case guarantee).
4. **Given** any changelist screen, **When** it renders, **Then** it presents the
   Django-admin-equivalent furniture: a result/object count, column-header row, and
   (where the model declares `list_filter`) a filter region — matching the web admin's
   information architecture as closely as the terminal allows.

---

### User Story 2 - Operator drives the entire TUI with the mouse (Priority: P2)

An operator who prefers the mouse (or is on a terminal where it is convenient) can run
the whole tool without memorizing key bindings. Clicking an app or model on the index
opens it. Single-clicking a changelist row focuses it; double-clicking (or clicking an
open/edit affordance) opens its detail. Clicking checkboxes/selection toggles multi-selects
rows.
Clicking pagination controls, column headers (to sort), filter options, action buttons,
and Save/Delete/Cancel buttons all work. The mouse wheel scrolls long lists and forms.
Every mouse-reachable action also remains reachable by keyboard; the mouse is additive,
not a replacement, and the on-screen affordances make the clickable targets discoverable.

**Why this priority**: the tool is currently keyboard-only, which is a real adoption
barrier; making it mouse-drivable widens who can use it without changing what it does.
It depends on US1 because clickable targets (rows, headers, controls) must first be laid
out stably.

**Independent Test**: against the sample project, a scripted/manual pass MUST complete a
full workflow — index → changelist → select rows → run an action / open a record → edit
→ save → return — using only mouse events, and an equivalent pass MUST complete using
only the keyboard. Both paths MUST reach the same end state and produce the same audit
entries.

**Acceptance Scenarios**:

1. **Given** the index screen, **When** the operator clicks an app section or a model
   entry, **Then** the same navigation occurs as pressing the corresponding key.
2. **Given** a changelist, **When** the operator single-clicks a row (focus), double-clicks
   a row or clicks its open link (detail), clicks a selection checkbox (multi-select),
   clicks a column header (sort), a filter option, or a pagination control, **Then** the
   focus / detail-open / multi-selection / sort / filter / page changes accordingly and
   matches the keyboard-driven result.
3. **Given** a detail, create, or edit form, **When** the operator clicks a field to
   focus it and clicks Save / Delete / Cancel / action buttons, **Then** the same
   focus-and-submit behavior occurs as the keyboard equivalents, including validation and
   confirmation steps.
4. **Given** any screen, **When** the operator uses the mouse wheel over a scrollable
   region, **Then** that region scrolls without altering selection or focus unexpectedly.
5. **Given** any action reachable by mouse, **When** the operator inspects the screen,
   **Then** the same action is also reachable by a documented key binding (mouse is
   additive, never exclusive).

---

### User Story 3 - Operator's create/edit saves succeed for every default field type (Priority: P1)

An operator opens create and edit forms for the sample project's models and saves them.
Every field type the default admin form produces — text, boolean, choice/enum, foreign
key, date/datetime, JSON, numeric, and nullable/blank variants — accepts input, validates
like the web admin, and **saves successfully**, writing the correct value and the correct
`LogEntry`. Edit paths that currently fail (the reported "some model edits not working")
are corrected, and a regression matrix prevents them from regressing again.

**Why this priority**: a save path that silently fails or errors is a correctness defect,
not a polish item — it undermines the core promise of v1 (edits identical to the web
admin). It shares P1 with US1 because both are "the tool is broken" reports, not
enhancements.

**Independent Test**: against the sample project, an automated matrix MUST create and
edit a record exercising each default widget/field type (including foreign keys,
date/datetime, JSON, boolean, choice, and null/blank handling) and assert that the save
succeeds, the persisted value is correct, validation errors surface on the right fields,
and the resulting `LogEntry` matches what the web admin would record. The matrix MUST
include whatever specific field/widget combinations are currently failing.

**Acceptance Scenarios**:

1. **Given** an edit form for a model whose fields cover the default widget set, **When**
   the operator changes a value of each field type and saves, **Then** the save succeeds
   and the persisted values match the submitted input for every field type.
2. **Given** a field/widget combination that currently fails to save, **When** the fix is
   in place and the operator saves a valid value, **Then** the save succeeds and a
   regression test for that combination passes (and would have failed before the fix).
3. **Given** an invalid value for any field type, **When** the operator submits it,
   **Then** the validation error appears on the correct field with the web admin's
   message and the record is not saved (preserving v1 behavior).
4. **Given** any successful create or edit, **When** it completes, **Then** the `LogEntry`
   attribution, action flag, and change message match the web admin's for the same input
   (preserving v1 FR-008).

---

### User Story 4 - Project owner controls the TUI's appearance through Django settings (Priority: P3)

A project owner wants the TUI to look a particular way without editing package code. They
set values under the existing `ADMIN_TUI` settings dict to control appearance — selecting
the visual theme (including a Django-admin-styled default and a way to fall back to a
neutral/minimal look), and optionally supplying their own theme override. Appearance
configuration is **optional**: with no appearance settings, the TUI uses a sensible
Django-admin-evoking default. Theming is expressed in the TUI framework's own theming
language (continuing v1 FR-029 / Constitution Principle), not a new parallel abstraction.

**Why this priority**: theming is valuable but not required for the tool to be correct or
usable; it is the lowest-risk slice and naturally lands after the layout, interaction, and
save fixes that everything else depends on.

**Independent Test**: against the sample project, launching with no appearance settings
MUST produce the default look; setting the appearance option(s) to a different supported
value MUST visibly change the presentation without affecting any data behavior
(permissions, result sets, saves, audit) or requiring per-model configuration. An invalid
appearance setting MUST be rejected at startup with a clear `ImproperlyConfigured`-style
message (consistent with the existing settings loader).

**Acceptance Scenarios**:

1. **Given** a project with no appearance configuration under `ADMIN_TUI`, **When** the
   operator launches the TUI, **Then** it renders with the default Django-admin-evoking
   theme and full functionality.
2. **Given** a project that sets a supported appearance option to a non-default value,
   **When** the operator launches, **Then** the presentation changes accordingly while
   all data behavior is unchanged.
3. **Given** an invalid appearance setting, **When** the package loads, **Then** it raises
   a clear configuration error naming the offending key (matching the existing settings
   validation behavior), and does not start a broken session.
4. **Given** an appearance change, **When** applied, **Then** no `ModelAdmin` or TUI
   overlay configuration must be added or changed for it to take effect.

---

### Edge Cases

- A cell value contains terminal control sequences, tabs, newlines, or zero-width /
  double-width (CJK, emoji) characters — the cell MUST truncate to its column width
  safely without breaking alignment of neighboring columns or the row below (extends v1's
  control-sequence edge case to the new truncation model).
- The terminal is resized while a changelist or form is open — the layout MUST reflow to
  the new size and re-truncate columns without losing the current selection, scroll
  position intent, or focus, and without crashing.
- A terminal or multiplexer (e.g. tmux/screen over SSH) does not report mouse events —
  the TUI MUST remain fully operable by keyboard and MUST NOT present mouse-only
  affordances that have no keyboard equivalent.
- A click lands on a non-interactive region (padding, header furniture) — the TUI MUST
  ignore it without changing selection, focus, or state.
- A configured/selected theme references a missing or malformed theme resource — startup
  MUST fail fast with an actionable message (per the existing settings loader), rather
  than launching into a broken display.
- A column is configured to display a very long single token with no break points — it
  MUST still truncate at the column boundary rather than overflowing.

## Requirements *(mandatory)*

### Functional Requirements

**Stable changelist layout & truncation (the glitch fix)**

- **FR-001**: The changelist MUST render columns at stable widths and rows at stable
  heights; changing the selected/highlighted row MUST NOT alter any column width, any row
  height, or the truncation of any cell.
- **FR-002**: Cell values that exceed their column width MUST be truncated with a visible
  truncation indicator (e.g. an ellipsis), and MUST remain truncated regardless of
  selection state.
- **FR-003**: The full, untruncated value of a cell MUST be reachable through opening the
  record detail view (the canonical place for the full record). Additionally, the full
  value of the currently focused cell MUST be previewable in a non-reflowing location
  (e.g. a footer/status bar) that does NOT resize the row, alter column widths, or shift
  any layout. The full value MUST NEVER be revealed by expanding/reflowing the row itself,
  and MUST NEVER appear merely as a side effect of selecting/highlighting a row beyond the
  fixed-size footer preview.
- **FR-004**: The changelist MUST present Django-admin-equivalent information architecture
  within terminal constraints: a column-header row with the admin's column labels, a
  result/object count, row selection highlight and multi-select indication, pagination
  controls, and (where declared) a filter region — without changing the result sets,
  ordering, search, filter, or pagination semantics established in v1.
- **FR-005**: When the terminal is narrower than the sum of the configured column widths,
  the changelist MUST keep each column at its stable width (truncating cell content as in
  FR-002) and MUST scroll horizontally — reachable by both keyboard and mouse — so that
  every declared column remains reachable. Columns MUST NOT be silently dropped, and the
  layout MUST NOT crash or corrupt (continuing the v1 narrow-terminal guarantee).

**Django visual parity** (resolved: full look-alike — replicate the admin's layout
*and* color palette as the default theme, within terminal constraints)

- **FR-006**: The TUI's screens (index, changelist, detail, forms, confirmations) MUST be
  a full look-alike of the Django admin within terminal constraints, replicating both its
  layout/information architecture AND its color palette as the default theme. This
  includes, at minimum: a branded header/title bar, a breadcrumb / location indicator, an
  object-tools row (e.g. "Add", history/related affordances) placed analogously to the
  web admin, sectioned forms whose fieldsets match the admin's grouping and ordering, a
  filter region positioned like the admin's filter sidebar, and the admin's
  blue/grey-family color scheme rendered with the terminal's color capabilities.
- **FR-006a**: The default bundled theme MUST evoke the standard Django admin palette
  (the admin's signature header/link/accent colors mapped to terminal colors); it is the
  look a project sees with no appearance configuration.
- **FR-007**: Visual parity work MUST NOT change any data behavior: result sets,
  permissions, validation, saves, deletes, actions, and audit MUST remain exactly as
  specified in v1.

**Mouse interaction (additive to keyboard)**

- **FR-008**: The TUI MUST react to mouse input across all screens: clicking navigational
  targets (apps, models, rows), selection toggles (multi-select), column headers (sort),
  filter options, pagination controls, and form/action buttons (Save, Delete, Cancel,
  run-action) MUST perform the same operation as the corresponding key binding.
- **FR-008a**: On the changelist, a single click MUST highlight/focus the clicked row
  (mirroring keyboard row movement, including the footer preview of FR-003); a
  double-click on a row — or a single click on an explicit "open" link/affordance — MUST
  open that record's detail. Multi-row selection MUST be performed through a dedicated
  selection checkbox/toggle column, not by single-clicking the row body.
- **FR-009**: Scrollable regions (changelist, long forms, lists) MUST respond to the mouse
  wheel for scrolling without unexpectedly changing the current selection or focus.
- **FR-010**: Every action reachable by the mouse MUST also remain reachable by a
  documented key binding; the mouse is strictly additive and the tool MUST remain fully
  operable on terminals that do not report mouse events.
- **FR-011**: Clickable affordances MUST be discoverable on screen (e.g. visible buttons,
  selectable rows/headers), and clicks on non-interactive regions MUST be ignored without
  side effects.

**Model edit/save correctness (bug fix)**

- **FR-012**: Create and edit forms MUST successfully save valid input for every field
  type the default admin form produces — text, boolean, choice/enum, foreign key,
  date/datetime, JSON, numeric — including nullable and blank variants, persisting the
  correct value.
- **FR-013**: Edit/save paths that currently fail MUST be corrected, and each corrected
  combination MUST be covered by a regression test that would have failed before the fix.
- **FR-014**: Validation, `readonly_fields` enforcement, lifecycle hooks, and `LogEntry`
  attribution/change-message behavior for saves MUST continue to match the web admin
  exactly (preserving v1 FR-013/FR-014/FR-015).

**Appearance configuration via settings** (resolved: named-theme selector + custom
theme-file override, with optional toggles, all under the existing `ADMIN_TUI` dict)

- **FR-015**: Appearance MUST be controllable through the existing single `ADMIN_TUI`
  project settings dict (no new top-level settings namespace), keeping the public
  configuration surface small (consistent with v1 FR-027). The exposed controls MUST be:
  (a) a **named-theme selector** that chooses among bundled themes — including the
  Django-admin default and at least one neutral/minimal alternative; (b) the existing
  **custom theme-file override** (the current `THEME` `.tcss` path) for projects that want
  to supply their own; and (c) optional presentation toggles (e.g. display density, and
  enabling/disabling mouse support) where they do not duplicate framework theming.
- **FR-015a**: The named-theme selector and the custom theme-file override MUST have a
  defined precedence (a supplied custom theme file overrides the named-theme selection),
  and selecting a non-existent named theme MUST be a configuration error (per FR-018).
- **FR-016**: Appearance configuration MUST be optional: with no appearance settings, the
  TUI MUST render with the default Django-admin-evoking bundled theme (FR-006a).
- **FR-017**: Theming MUST be expressed in the TUI framework's own theming language; the
  package MUST NOT introduce a parallel theming abstraction (preserving v1 FR-029 /
  Constitution).
- **FR-018**: Invalid appearance settings MUST be rejected at load time with a clear,
  actionable configuration error that names the offending key (consistent with the
  existing settings loader behavior).
- **FR-019**: Appearance changes MUST take effect without requiring any `ModelAdmin` or
  TUI overlay configuration, and MUST NOT alter any data behavior.

**Scope & public surface preservation**

- **FR-020**: This feature MUST NOT re-derive any admin behavior (querysets, search,
  filter, ordering, pagination, forms, validation, permissions, actions, audit); it reuses
  the v1 paths (preserving v1 FR-006).
- **FR-021**: Any additions to the documented public API surface (e.g. new appearance
  settings keys or overlay rendering hooks) MUST follow the v1 governance: written
  justification, regression test, and documentation entry (preserving v1 FR-030/FR-031).

### Key Entities *(include if feature involves data)*

- **Changelist layout**: the computed, stable column widths, truncation rules, and
  row/selection presentation for a model's changelist; derived from the admin's
  `list_display` and the current terminal size, independent of which row is selected.
- **Appearance configuration**: the optional set of values under `ADMIN_TUI` that select
  the theme/look; resolves to a concrete TUI-framework theme, with a Django-admin-evoking
  default when unset.
- **Mouse target**: an on-screen region bound to the same operation as a key binding
  (navigate, select, sort, filter, paginate, submit, run action), with a guaranteed
  keyboard equivalent.
- (Reuses v1 entities unchanged: Session, Site registry, TUI overlay, Widget registry,
  Audit entry.)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On the sample project, navigating a changelist whose cells overflow their
  columns produces zero changes to column widths, row heights, or cell truncation as the
  selection moves across 100% of rows — verified by an automated layout-stability test
  (the current cropping/expand-on-select behavior would fail it).
- **SC-002**: A complete operator workflow (index → changelist → multi-select → run action
  or open record → edit → save → return) is completable using only mouse events, and
  separately using only keyboard events, with both reaching the same end state and
  producing identical audit entries.
- **SC-003**: 100% of the default field/widget types (text, boolean, choice, foreign key,
  date/datetime, JSON, numeric, plus null/blank variants) in the sample project's
  create/edit matrix save valid input successfully with the correct persisted value and
  `LogEntry`; every previously-failing combination is covered by a test that fails on the
  pre-fix code and passes after.
- **SC-004**: With no appearance settings, the TUI launches with the default theme; setting
  a supported appearance option to a non-default value visibly changes the presentation
  with no change to result sets, permissions, saves, or audit — verified by a test that
  compares data behavior across themes and asserts it identical.
- **SC-005**: An invalid appearance setting causes startup to fail within 1 second with a
  non-zero exit and a one-line, actionable message naming the offending key — no broken
  TUI screen is shown (consistent with v1 SC-008).
- **SC-006**: The TUI remains fully operable by keyboard on a terminal with mouse reporting
  disabled — every workflow in SC-002 completes keyboard-only with no mouse-exclusive dead
  ends.
- **SC-007**: All v1 success criteria (SC-001..SC-008 of `001-admin-tui-mvp`) continue to
  pass unchanged after the redesign — the redesign is presentation/interaction/bug-fix
  only and introduces no data-behavior regressions.

## Assumptions

- The v1 functional core (`001-admin-tui-mvp`) is complete and correct except for the
  specific edit/save defects this feature fixes; v2 builds on it rather than replacing it.
- "Match the Django UI (nearest possible)" means evoking the web admin's information
  architecture and visual structure within terminal constraints — not pixel-for-pixel
  reproduction, which a terminal cannot achieve.
- The TUI framework in use (Textual) supports mouse events and a theming language; mouse
  and theming are implemented through the framework's native facilities, not a new
  abstraction (per Constitution / v1 FR-029).
- The specific "model edits not working" are concrete, reproducible defects that will be
  enumerated by building the field/widget save matrix against the sample project during
  planning/triage; the spec commits to fixing all of them and locking them with tests.
- Appearance settings live under the existing `ADMIN_TUI` dict and are validated by the
  existing settings loader (`admin_tui/conf.py`), which already supports a `THEME` key.
- Terminal capability assumptions from v1 hold (ANSI color, ≥ 80×24, graceful degradation
  in scope); optimization for legacy/unusual terminals remains out of scope.

## Dependencies

- The completed v1 feature and its test suite (the redesign must keep v1's tests green).
- The TUI framework's mouse-event and theming support.
- The existing `ADMIN_TUI` settings loader and its validation path.
- The in-repo sample project, extended as needed to exercise the layout-stability, mouse,
  save-matrix, and theming tests.

## Out of Scope (v2)

- Any change to v1's data behavior: result sets, search/filter/sort/pagination semantics,
  permission checks, validation rules, audit logging, or the action model.
- New functional capabilities beyond v1's CRUD + actions (no new admin features).
- Re-deriving or bypassing any `ModelAdmin`/admin internals (continues v1 FR-006/FR-022).
- A remote/headless/multi-user mode, network port, or token (remains out of scope per v1).
- Pixel-perfect or image-based reproduction of the web admin; web-admin customizations
  outside the standard declarative surface (custom templates/JS) remain out of scope.
- A theme marketplace, downloadable themes, or runtime theme hot-swapping beyond what the
  settings-driven selection provides.
