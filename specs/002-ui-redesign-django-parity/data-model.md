# Phase 1 Data Model — UI Redesign & Django Parity (v2)

v2 adds **no persistent data** and no new domain entities. It introduces a handful of
**in-memory view-state** structures that live on a screen for the duration of a render.
They are all derived from data the v1 screens already hold (`ChangeList`, the focused
object, settings) — never a second source of truth. The v1 entities (Session, Site
registry, TuiAdmin overlay, Widget registry, Audit entry) are reused unchanged.

---

## ColumnSpec  *(internal — `admin_tui/widgets/layout.py`)*

One per changelist column, computed once per `_rebuild()` and independent of selection.

| Field | Type | Notes |
|-------|------|-------|
| `key` | `str` | The `list_display` column name (or `SELECTION_COLUMN_KEY`). |
| `label` | `str` | Admin column label (`label_for_field`), as today. |
| `width` | `int` | Computed display width. `clamp(len(label), max_page_cell_width, MIN_COL=6, MAX_COL=40)`; selection column fixed at 3. |
| `align` | `"left" \| "right"` | Right for numeric columns, left otherwise (cosmetic). |

**Derivation.** `compute_column_widths(columns, page_rows, caps) -> list[ColumnSpec]`.
Pure function; samples only the current page's rendered cell strings. **Invariant
(SC-001):** output depends only on `(columns, page_rows, caps)` — never on which row is
focused/selected. Re-derived on search / filter / sort / page change; NOT on cursor move.

**Truncation.** `truncate_cell(value: str, width: int) -> str`: strip control
chars/newlines/tabs; if `cell_len(value) > width`, cut to `width-1` display cells (CJK /
emoji aware via `rich.cells`) and append `…`. Output `cell_len` is always ≤ `width`.

---

## CellPreview  *(internal — changelist footer status bar `#cell-preview`)*

| Field | Type | Notes |
|-------|------|-------|
| `text` | `str` | Full, untruncated display value of the **currently focused** cell. |

**Derivation.** Recomputed on `RowHighlighted` / `CellHighlighted` from
`overlay.render_cell(request, obj, col).display`. Rendered in a fixed 1-line bar; updating
it never changes column widths, row heights, or scroll (FR-003 / Q1).

---

## FilterEntry & FilterPanelState  *(internal — `admin_tui/widgets/filters.py`)*

Surfaces Django's own `list_filter` specs; no filter logic is re-derived (Constitution I).

**FilterPanelState** (rebuilt each `_rebuild()` when `list_filter` is non-empty):

| Field | Type | Notes |
|-------|------|-------|
| `groups` | `list[FilterGroup]` | One per `filter_spec` from `changelist.get_filters(request)`. |

**FilterGroup**

| Field | Type | Notes |
|-------|------|-------|
| `title` | `str` | `filter_spec.title`. |
| `entries` | `list[FilterEntry]` | From `filter_spec.choices(changelist)`. |

**FilterEntry**

| Field | Type | Notes |
|-------|------|-------|
| `display` | `str` | Choice label (e.g. "All", "Yes", "No"). |
| `selected` | `bool` | From the choice dict. |
| `query_string` | `str` | Django-built querystring for this choice. |

**Transition.** Selecting an entry merges its `query_string` params into
`self.query_params` and calls `_reset_request_and_rebuild()`. The resulting result set is
Django's, identical to the web admin for the same params (FR-004, FR-007).

---

## AppearanceConfig  *(internal — resolved in `admin_tui/conf.py` + applied in `app.py`)*

| Field | Type | Source | Notes |
|-------|------|--------|-------|
| `theme_name` | `str` | `ADMIN_TUI["THEME_NAME"]` or `--theme-name`; default `"django"` | Must be a registered theme name at launch, else `ImproperlyConfigured` (FR-018). |
| `css_override` | `Path \| None` | `ADMIN_TUI["THEME"]` or `--theme` (existing) | Existing `.tcss` validation. Layered over the theme; overrides where they overlap (FR-015a). |

**State transition (launch).**
`ready()` validates/freezes config → CLI flags may override on the `TuiSession` →
`App` registers bundled themes → sets `self.theme = theme_name` → applies `CSS_PATH =
css_override` if present. No `settings.ADMIN_TUI` read after `ready()` (unchanged rule).

**Invariant (SC-004).** Changing `theme_name`/`css_override` changes only presentation;
result sets, permissions, saves, and audit are byte-for-byte unaffected.

---

## MouseTarget  *(conceptual — see `contracts/interaction.md`)*

Not a stored object; the mapping of on-screen regions to operations, each with a guaranteed
keyboard equivalent (FR-008/010). Enumerated in the interaction contract: app/model rows,
data rows (single=focus / double=open), selection checkboxes, column headers (sort), filter
entries, pagination buttons, object-tools (Add), and form/action buttons.

---

## SaveData (edit/create gather)  *(internal — `admin_tui/screens/change.py`)*

Not new state, but its **shape** is corrected in v2 (D8). `_gather_data()` produces the
dict fed to `_build_form(..., data=...)`:

| Widget kind | Produced value | v2 change |
|-------------|----------------|-----------|
| `Input` (text/number/date/datetime) | `str` | unchanged |
| `Switch` (boolean) | `"True"`/absent | confirm unchecked → absent/False semantics |
| `Select` (FK / choice) | `str(pk)` or `""` | unchanged |
| **`SelectMultiple` / multi-value (M2M)** | **`list[str]` of pks** | **NEW: was dropped → now gathered** |
| **MultiWidget (split fields)** | **per-subwidget keys** | **NEW: handled** |

**Invariant (FR-014).** Regardless of gather shape, the save still runs
`get_form → is_valid → save_model → save_related → log_addition/log_change` unchanged.
The edit rebind MUST pass `instance=obj` so a save updates (not inserts).
