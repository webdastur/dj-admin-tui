# Implementation Plan: Django Admin TUI — UI Redesign & Django Parity (v2)

**Branch**: `002-ui-redesign-django-parity` | **Date**: 2026-05-30 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/002-ui-redesign-django-parity/spec.md`

## Summary

v2 is a **presentation, interaction, and bug-fix pass** over the completed v1 core. It
does four things, in priority order, without changing any v1 data behavior:

1. **Fix the changelist glitch (P1)** — the current `DataTable` auto-sizes columns to the
   widest cell and auto-scrolls horizontally to keep the cursor cell visible, which reads
   as "columns cropped, full text revealed on select." We replace that with a
   **selection-independent fixed-width layout**: each column gets a width computed once
   per rebuild (from `list_display` + a page-content sample, capped), cells are truncated
   with an ellipsis, and overflow is handled by intentional horizontal scrolling — never
   by reflow on selection. The focused cell's full value is shown in a non-reflowing
   footer status bar.
2. **Fix model edits (P1)** — build a field/widget **save matrix** in the sample project
   covering every default widget (text, boolean, choice, FK, M2M, date/datetime, JSON,
   numeric, null/blank), reproduce the reported failures, root-cause them in
   `screens/change.py` (`_gather_data` / `_read_widget_value` / form re-binding), fix, and
   lock each with a regression test.
3. **Add mouse support (P2)** — single-click focuses a row, double-click (or an open link)
   opens the detail, a dedicated checkbox column multi-selects, header clicks sort, the
   filter sidebar and pagination controls are clickable, and the wheel scrolls. Every
   mouse target keeps its keyboard equivalent (Textual is mouse-on by default; keyboard
   parity is preserved).
4. **Django visual parity + settings-driven theming (P3)** — restyle every screen into a
   full Django-admin look-alike (branded header bar, breadcrumb, object-tools row,
   sectioned fieldsets, a filter sidebar like the admin's, the admin's blue/grey palette)
   and ship it as a bundled Textual `Theme`. Appearance is selected through the existing
   `ADMIN_TUI` dict via one new key, `THEME_NAME`, layered with the existing `.tcss`
   `THEME` override.

All admin behavior continues to flow through `ModelAdmin` + Django internals
(Constitution I); permissions and audit are untouched (Constitution II); the redesigned
default screens remain the synthesized-overlay path third-party code uses (Constitution
IV); customization is still raw Textual primitives (Constitution VI).

## Technical Context

**Language/Version**: Python 3.12+ (unchanged from v1 — Django 6.0 requires 3.12+).

**Primary Dependencies** (unchanged snapshot from v1, re-verified 2026-05-30):

- **Django** — 4.2 LTS / 5.2 LTS / 6.0 test matrix. The v2 filter sidebar reuses
  `ChangeList.get_filters(request)` and the `filter_spec.choices(changelist)` /
  `querystring` surface; sorting still uses Django's `o` query param. No new admin
  internals beyond those documented in v1's `contracts/internal-django-surface.md` plus
  the filter-spec surface added in this feature's contract.
- **Textual** `>=8.2,<9`. v2 relies on these Textual facilities, all present in 8.x:
  - `DataTable.add_column(..., width=N)` for fixed-width columns; manual cell truncation.
  - `events.Click.chain` (==2 for double-click) to distinguish single vs. double click.
  - `DataTable` messages `RowHighlighted` / `CellHighlighted` (footer preview),
    `HeaderSelected` (click-to-sort), `CellSelected` (checkbox-column click).
  - `textual.theme.Theme` + `App.register_theme(...)` + `App.theme = "<name>"` for the
    named-theme selector; `App.CSS_PATH` (existing) for the `.tcss` override, layered on
    top of theme variables.
  - Mouse is enabled by default; `Button`, `ListView`, scroll containers already accept
    clicks/wheel.
- **rich** — transitive via Textual; not pinned by us. Truncation uses Textual/Rich cell
  width measurement (handles double-width CJK / emoji) — see research D1.

**Dev/test dependencies** (unchanged): `pytest`, `pytest-django`, `pytest-asyncio`,
Textual `Pilot` (headless `run_test()`), the in-repo `sample_project/`.

**Storage**: host project's Django database; no new store (unchanged).

**Testing**: `pytest` + Textual `Pilot`. New v2 suites: layout-stability (snapshot column
widths/row heights across cursor moves), mouse-vs-keyboard parity, the create/edit save
matrix, and appearance (default theme + `THEME_NAME` switch + invalid-theme rejection).
`Pilot.click`, `Pilot.hover`, and key presses drive both interaction modes headlessly.

**Target Platform**: any OS with a modern terminal emulator (ANSI color, ≥80×24, mouse
reporting where available). Linux + macOS primary; mouse degrades gracefully to
keyboard-only.

**Project Type**: single Python package (`admin_tui/`) + sample project + tests
(unchanged structure; v2 edits existing modules and adds a bundled theme + filter widget).

**Performance Goals**: v1's SC-002 (changelist page-transition p95 < 300 ms on 100k rows,
memory bounded by `list_per_page`) MUST continue to hold. The new fixed-width layout
samples only the **current page** for column sizing — never the full queryset — so it adds
no per-row cost beyond the page already loaded.

**Constraints**: no network port, no new persistent state, single process (Constitution
VII, unchanged). The redesign MUST NOT alter any result set, permission check, validation
rule, save semantics, or audit entry (spec FR-007/FR-020, SC-007).

**Scale/Scope**: edits to `screens/changelist.py`, `screens/change.py`,
`screens/index.py`, `screens/action_confirm.py`, `app.py`, `conf.py`; one new bundled
theme module; one new filter-sidebar widget; one new layout/truncation helper; sample
project + tests extended. Public Python API surface is unchanged; one new **settings key**
(`THEME_NAME`) is added under the existing dict (FR-031 governance applied).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| # | Principle | Gate (must hold true) | Result |
|---|-----------|----------------------|--------|
| I | Reuse Django's admin | No code path computes filtering, validation, ordering, or permission logic Django provides. | ✅ The new filter sidebar is built from `ChangeList.get_filters(request)` and applies Django's own `querystring`; sort still uses Django's `o` param; the changelist is still rebuilt via `_build_changelist`. Layout/truncation is pure presentation over `result_list`. |
| II | Permission & audit fidelity | Every read passes `has_view_permission`; every mutation passes the relevant `has_*_permission` AND emits a `LogEntry`. | ✅ The save-bug fix changes only how widget values are *gathered* into form data; it still routes through `get_form` → `is_valid` → `save_model`/`save_related` → `log_addition`/`log_change`. Mouse/theme touch no permission or audit path. |
| III | Zero-config by default | A project with `ModelAdmin`s and no `tui.py` works fully, now including the redesigned look. | ✅ Default theme, layout, filter sidebar, and mouse all work with zero overlay/TUI config. `plain_app` (no `tui.py`) exercises this (SC-007). |
| IV | Defaults travel the extension path | Redesigned default behavior is produced by the synthesized-overlay path, not a parallel branch. | ✅ Redesigned screens are still returned by `overlay.get_changelist_screen` / `get_detail_screen`; the default overlay is the synthesized `TuiAdmin`. No privileged render path is introduced. |
| V | Small, intentional, stable public API | Public Python surface stays at the six v1 names + documented hooks. New config follows FR-031 (justification + test + docs). | ✅ No new public Python name. One new **settings key** `THEME_NAME` — justified (spec FR-015, user-selected), tested (appearance suite), documented (`contracts/settings.md`, `quickstart.md`). Density/mouse toggles **deferred** (Principle V: no demonstrated need; keyboard parity already guaranteed) — see research D9. |
| VI | Build on Textual; don't wrap it | UI uses Textual primitives (Theme, DataTable, Click, CSS) directly; no abstraction layer. | ✅ Named themes are `textual.theme.Theme` objects; the override is Textual CSS; clicks/wheel are Textual events; truncation uses Textual cell-width measurement. Customizers still subclass `Screen`/`Widget` and set `App.theme`. |
| VII | Local-first security posture | No network port, no token, no remote API; trust model unchanged. | ✅ v2 is in-process rendering/interaction only; nothing about the trust boundary changes. |
| VIII | Sample app covers every extension point | Sample exercises the new paths; CI fails if any breaks. | ✅ Sample gains long-value columns (truncation), `list_filter` (filter sidebar), a full-widget model (save matrix), and theme assertions. v1's overlay/widget/native-action coverage is retained. |

**Result**: PASS. No violations to record in Complexity Tracking. The single new settings
key is governed by FR-031, not a constitution deviation.

## Project Structure

### Documentation (this feature)

```text
specs/002-ui-redesign-django-parity/
├── plan.md              # This file (/speckit-plan output)
├── spec.md              # Feature spec (written + clarified)
├── research.md          # Phase 0 — locked decisions (layout, mouse, theming, edit-bug triage)
├── data-model.md        # Phase 1 — v2 view-state entities (layout, preview, filter, appearance)
├── quickstart.md        # Phase 1 — theming-via-settings + mouse walkthrough (delta over v1)
├── contracts/           # Phase 1 — v2 contract deltas
│   ├── settings.md              # ADMIN_TUI dict with the new THEME_NAME key (full table)
│   ├── interaction.md           # keymap + mouse map + changelist layout/filter/pagination contract
│   └── theming.md               # bundled themes, custom Theme registration, .tcss precedence
├── checklists/
│   └── requirements.md  # spec quality checklist (passing)
└── tasks.md             # Phase 2 output (created by /speckit-tasks, NOT here)
```

### Source Code (repository root) — v2 touch map

```text
admin_tui/
├── app.py                       # CHANGED: register bundled themes; resolve THEME_NAME →
│                                #   App.theme; keep THEME (.tcss) as CSS_PATH override.
├── conf.py                      # CHANGED: add THEME_NAME key + validation (registered
│                                #   theme name; precedence vs THEME).
├── themes/                      # NEW (internal): bundled Textual Theme objects.
│   ├── __init__.py              #   _register_bundled_themes(app); name constants.
│   └── django.py                #   "django" (admin blue/grey) + a neutral fallback.
├── widgets/
│   ├── layout.py                # NEW (internal): compute_column_widths(columns, rows,
│   │                            #   caps) + truncate_cell(value, width) — selection-
│   │                            #   independent, page-sampled, CJK/emoji-safe (D1).
│   └── filters.py               # NEW (internal): FilterSidebar widget built from
│                                #   ChangeList.get_filters(request) (D4).
├── screens/
│   ├── index.py                 # CHANGED: Django-look header/breadcrumb; clickable
│   │                            #   app/model rows (mouse parity).
│   ├── changelist.py            # CHANGED: fixed-width truncated columns (D1); footer
│   │                            #   cell-preview status bar (D2); single/double-click +
│   │                            #   checkbox-column select + header-click sort (D3);
│   │                            #   filter sidebar (D4); clickable pagination (D5);
│   │                            #   object-tools row (Add).
│   ├── change.py                # CHANGED: edit/save bug fix in _gather_data /
│   │                            #   _read_widget_value / form re-bind (D8); Django-look
│   │                            #   fieldset sections; clickable Save/Cancel already work.
│   └── action_confirm.py        # CHANGED: restyle to admin confirm look; clickable buttons.
└── (core/, _internal/, options.py, sites.py, management/ — UNCHANGED behavior)

sample_project/
├── library/
│   ├── models.py                # CHANGED: add a wide-text field + a model covering the
│   │                            #   full default-widget set for the save matrix.
│   ├── admin.py                 # CHANGED: add list_filter + a long-value list_display
│   │                            #   column to exercise the filter sidebar + truncation.
│   └── (tui.py, fields.py, tui_widgets.py — retained; v1 extension coverage kept)
└── plain_app/                   # UNCHANGED: zero-config parity check (SC-007)

tests/
├── unit/
│   ├── test_layout.py           # NEW: compute_column_widths/truncate_cell incl. CJK/emoji,
│   │                            #   long single token, narrow viewport (FR-001..005).
│   └── test_appearance_conf.py  # NEW: THEME_NAME validation + precedence (FR-015a/018).
└── integration/sample_project/
    ├── test_changelist_layout.py# NEW: layout stability across cursor moves (SC-001);
    │                            #   filter sidebar = web-admin result parity (FR-004).
    ├── test_mouse.py            # NEW: mouse-only vs keyboard-only full workflow (SC-002/006).
    ├── test_save_matrix.py      # NEW: every widget/field saves correctly (SC-003).
    └── test_theming.py          # NEW: default theme + THEME_NAME switch leaves data
                                 #   behavior identical (SC-004); invalid theme fails (SC-005).
```

**Structure Decision**: Same single-package layout as v1. v2 is mostly *edits to existing
screens* plus three small **internal** modules (`themes/`, `widgets/layout.py`,
`widgets/filters.py`) — all underscore-internal, none added to the public surface. This
keeps Constitution V intact (one new settings key, zero new public Python names) while
delivering the redesign through the same screens that are the synthesized-overlay path
(Constitution IV). The new helpers are isolated and unit-testable (`compute_column_widths`,
`truncate_cell`) so the layout-stability guarantee (SC-001) is verifiable without a full
TUI.

## Complexity Tracking

> Fill ONLY if Constitution Check has violations that must be justified.

No constitution violations. The one addition that could look like scope creep — the new
`THEME_NAME` settings key — is the minimum surface that satisfies FR-015's user-selected
"named themes + override" and is governed by FR-031 (justified, tested, documented), not a
deviation. Density/mouse toggles were considered and deliberately deferred (research D9).

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| *(none)*  | —          | —                                   |
