# Contract: Interaction surface (keyboard + mouse) and changelist layout

This is the v2 UI contract for the application: the keymap, the mouse map, and the
changelist layout/filter/pagination behavior. **Invariant (FR-010):** every mouse target
has a keyboard equivalent; the tool is fully operable with no mouse.

---

## Global

| Operation | Key | Mouse |
|-----------|-----|-------|
| Quit | `q` (top-level) | — |
| Help | `?` | — |
| Back / Cancel | `q` / `Esc` | click a `Back`/`Cancel` button where shown |

---

## Index screen

| Operation | Key | Mouse |
|-----------|-----|-------|
| Open an app/model | arrows + `Enter` | **single click** the app section / model row |

Look: branded header bar + breadcrumb (`Home`). Apps and models grouped as in the admin
index.

---

## Changelist screen

### Keymap (retained from v1)

`q` back · `/` search · `s` sort current column · `a` add · `Space` toggle row select ·
`x` actions · `PgUp`/`PgDn` page · `Enter` open detail.

### Mouse map (v2)

| Operation | Mouse | Keyboard equivalent |
|-----------|-------|---------------------|
| Focus a row | **single click** on the row body | arrow keys |
| Open detail | **double click** on the row body, or click the row's open affordance | `Enter` |
| Toggle row selection (multi-select) | click the **checkbox column** cell | `Space` |
| Sort by a column | click the **column header** | `s` (on the focused column) |
| Apply / clear a filter | click a **filter entry** in the sidebar | focus sidebar + `Enter` |
| Previous / next page | click **‹ Prev** / **Next ›** | `PgUp` / `PgDn` |
| Add a record | click **+ Add** (object-tools) | `a` |
| Scroll | mouse **wheel** over the table | arrows / PgUp / PgDn |

**Click rules.** A single click never opens detail (only focuses). A click on a
non-interactive region (padding, header furniture) is ignored — no focus/selection change
(FR-011). Wheel scrolling never changes the focused row or selection (FR-009).

### Layout contract (FR-001..005, SC-001)

- Columns have **fixed, pre-computed widths** (see `data-model.md` → ColumnSpec). Widths
  are a function of `(columns, current-page rows, caps)` only — **independent of which row
  is focused/selected**. They change only on search / filter / sort / page change.
- Every cell is **truncated** to its column width with a trailing `…` when it overflows
  (CJK / emoji aware). Truncation does not depend on selection.
- The **focused cell's full value** appears in a fixed 1-line footer preview bar; nothing
  else reveals untruncated text in the table (FR-003 / Q1).
- When summed column widths exceed the viewport, the table **scrolls horizontally**
  (keyboard + wheel); **no column is dropped** and the layout never reflows on selection
  (FR-005).

### Filter sidebar (FR-004, Constitution I)

Shown only when the model declares `list_filter`. Each group/title and its entries come
from `changelist.get_filters(request)` / `filter_spec.choices(changelist)`; selecting an
entry applies Django's own `query_string`. The TUI never computes a filter predicate.

### Object tools & pagination

Object-tools row near the header carries **+ Add** (gated by `has_add_permission`).
Pagination region carries **‹ Prev**, `page N / M`, **Next ›**.

---

## Detail / Create / Edit screen

| Operation | Key | Mouse |
|-----------|-----|-------|
| Edit (from view) | `e` | — (open via row double-click → `Edit`) |
| Save | `Ctrl+S` | click **Save** |
| Cancel / back | `q` / `Esc` | click **Cancel** |
| Focus a field | `Tab` / arrows | **click** the field widget |

Look: header bar + breadcrumb (`Home › App › Model › Object`), admin-style fieldset
sections, submit-row buttons. `readonly_fields` render as plain text (no widget), unchanged
from v1.

---

## Save correctness (FR-012..014)

On Save, gathered widget values (including **M2M / multi-value** and **MultiWidget** fields,
fixed in v2 — see `data-model.md` → SaveData) are rebound via `_build_form(..., obj,
data=...)` with `instance=obj` and validated by Django; on success the v1 sequence
(`save_model` → `save_related` → `construct_change_message` → `log_addition`/`log_change`)
runs unchanged. Validation errors render per-field; the record is not saved.
