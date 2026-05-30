# Phase 0 Research — UI Redesign & Django Parity (v2)

All decisions below are locked for v2. Each carries rationale and the alternatives
rejected. They resolve every "NEEDS CLARIFICATION" the plan's Technical Context could
raise; the two spec-level clarifications were already settled in `spec.md` §Clarifications.

---

## D1 — Stable, selection-independent column layout + truncation (FR-001..005, SC-001)

**Decision.** Replace Textual `DataTable`'s default content-based auto-sizing with
explicitly-sized columns and pre-truncated cell strings.

- On each `_rebuild()` (search / filter / sort / page change — NOT on cursor move), compute
  a width per column via a pure helper `compute_column_widths(columns, page_rows, caps)`:
  - selection checkbox column: fixed width 3.
  - each data column: `width = clamp(len(header_label), max_cell_width_on_current_page,
    MIN_COL=6, MAX_COL=40)`. Only the **current page's** rows are sampled (never the full
    queryset — preserves SC-002 memory bound).
  - widths depend only on the page's data + the column set, never on which row is
    selected → stable across cursor movement (SC-001).
- `add_column(label, key=col, width=w)` with the computed width.
- Truncate every cell with `truncate_cell(value, w)`: measure display width with Rich's
  cell-width function (`rich.cells.cell_len`) so double-width CJK / emoji and zero-width
  marks are accounted for; if it overflows, cut to `w-1` display cells and append `…`.
  Strip control chars / newlines / tabs first (extends v1's control-sequence edge case).
- Let the table scroll **horizontally** when the summed widths exceed the viewport
  (FR-005). DataTable does this natively; the key change is that columns no longer expand
  to content and the cursor no longer triggers a reflow.

**Rationale.** The reported glitch is exactly DataTable's defaults: columns auto-size to
the widest cell (so wide cells "crop" the viewport) and the table auto-scrolls
horizontally to keep the cursor cell visible (so selecting a row "reveals the full text").
Fixed widths + pre-truncation makes width a function of (columns, page), not of selection,
which is the precise, unit-testable invariant SC-001 asserts.

**Alternatives rejected.**
- *Let DataTable auto-size, just disable cursor auto-scroll.* Rejected: still leaves
  unbounded column widths that crop the viewport; doesn't give a truncation indicator.
- *Wrap long cells to multiple lines (variable row height).* Rejected: variable row height
  reflows the table and breaks the "stable row height" half of SC-001; Django's changelist
  is single-line per cell too.
- *Fit-to-viewport (shrink columns to always fit, no horizontal scroll).* Rejected: the
  clarify session chose horizontal scroll so no column is ever dropped/over-squeezed
  (spec FR-005). Fitting would make wide-column models unreadable.

---

## D2 — Focused-cell full value via a non-reflowing footer preview (FR-003, Q1)

**Decision.** Add a single-line status bar (`Static`, id `#cell-preview`) docked just above
the `Footer`. On `DataTable.RowHighlighted` / `CellHighlighted` (cursor move, keyboard or
mouse), recompute the **focused cell's full untruncated value** from the underlying object
(`overlay.render_cell(...).display`) and write it to that bar. Height is fixed at 1 line;
it never resizes the table or a row.

**Rationale.** Directly implements the clarified Q1 answer: detail view stays canonical,
but the operator gets the full focused value without opening the record and without any
layout shift. Driving it off the highlight event keeps it in sync with both input modes.

**Alternatives rejected.**
- *Tooltip / popover on hover.* Rejected: tooltips are mouse-only (fails keyboard parity,
  FR-010) and Textual tooltips can overlay/obscure rows.
- *Expand the focused row to full height.* Explicitly forbidden by the spec (the original
  complaint).

---

## D3 — Changelist mouse model: single=focus, double=open, checkbox=select, header=sort (FR-008/008a, Q2)

**Decision.**
- Stop opening detail from `DataTable.RowSelected`. Instead:
  - **Single click / arrow keys** → move the cursor (focus) only; updates the D2 preview.
  - **Double click** → open detail. Detect via screen-level `on_click` checking
    `event.chain == 2` over the table body; **Enter** keeps opening detail (keyboard
    equivalent).
  - **Selection checkbox column**: a click whose resolved cell key is
    `SELECTION_COLUMN_KEY` toggles that row's membership in `selected_pks` (mouse path for
    the existing **Space** binding). The column header shows a ☐/☑ glyph.
  - **Column header click** → `DataTable.HeaderSelected` → run the same sort cycle as the
    **s** key for that column.
- Wheel scrolling is native to DataTable / scroll containers (FR-009); we only ensure the
  wheel does not change `cursor`/selection (default behavior — verified by test).

**Rationale.** Mirrors both Django (a row's link opens the object) and the existing
keyboard model (move + Enter), and prevents an accidental single stray click from
navigating. `event.chain` is Textual's documented multi-click counter; `HeaderSelected`
is the documented header-click message.

**Alternatives rejected.**
- *Single click opens detail.* Rejected in clarify (Q2-B): too easy to misnavigate, and
  it conflicts with single-click-to-focus needed for the preview.
- *Click row body toggles selection.* Rejected (Q2-C): overloads the most common click;
  a dedicated checkbox column matches the web admin's action checkboxes.

---

## D4 — Filter sidebar from Django's own filter specs (FR-004, Constitution I)

**Decision.** Add an internal `FilterSidebar` widget (a right-docked panel, like the
admin's filter sidebar) shown only when the model declares `list_filter`. Build it from the
`ChangeList` already produced by `_build_changelist`:
`changelist.get_filters(request)` → for each `filter_spec`, render its title and
`spec.choices(changelist)` entries (each entry carries `display`, `selected`, and a
`query_string`). Selecting an entry (click or keyboard) applies that filter by merging the
filter's query params into `self.query_params` and rebuilding — Django computes the
predicate, we never do.

**Rationale.** v1 supported filter *result-set parity* via query params but never surfaced
a filter UI. The cleanest, Constitution-I-correct way to add one is to render Django's own
filter choices and reuse their `query_string`, so filtering logic stays 100% Django's.

**Alternatives rejected.**
- *Build our own filter inputs per field type.* Rejected: re-derives filter semantics
  (violates Constitution I) and drifts from custom `list_filter` classes.
- *Modal filter picker (like the action picker).* Rejected: the admin's filter sidebar is
  persistent and is part of the "look-alike" target (FR-006); a modal hides current state.

---

## D5 — Clickable pagination + object-tools (FR-004, FR-008)

**Decision.** Render a footer/region with `[‹ Prev]`, a `page N / M` indicator, and
`[Next ›]` as Textual `Button`s (clickable + keyboard PgUp/PgDn retained), and an
object-tools row near the header with an `[+ Add]` button (mirrors the **a** binding,
gated by `has_add_permission`). These are plain Textual `Button`s, so they already accept
clicks and are keyboard-focusable.

**Rationale.** Pagination and "Add" are the two affordances the web admin exposes as
explicit controls; making them buttons satisfies mouse parity (FR-008) and the
look-alike (FR-006) with no bespoke widgets.

**Alternatives rejected.** Keeping pagination keyboard-only — fails FR-008 mouse parity.

---

## D6 — Theming: bundled Textual `Theme` objects + `THEME_NAME` selector, layered with the `.tcss` override (FR-015..019, Constitution VI)

**Decision.**
- Ship bundled themes as `textual.theme.Theme` objects in `admin_tui/themes/`:
  - **`django`** (default): the admin's palette — its signature header green/blue, link
    blue, and neutral greys mapped to Textual theme variables (`primary`, `secondary`,
    `accent`, `background`, `surface`, `foreground`, etc.).
  - a **neutral** fallback for operators who want a plain look (we re-expose a Textual
    built-in such as `textual-dark` by name rather than authoring a second palette).
- `App.__init__`/`on_mount` registers the bundled theme(s) via `register_theme(...)` and
  sets `self.theme = <resolved THEME_NAME>` (default `"django"`).
- The existing **`THEME` (`.tcss`) override** stays as `CSS_PATH` and is layered *on top*
  of the selected theme's variables. Precedence (FR-015a): the named theme provides the
  palette/variables; the `.tcss` file may override any rule and therefore "wins" wherever
  the two overlap. A custom theme file alone is sufficient (it can ignore the palette).
- New settings key **`THEME_NAME`**: `str | None`, default `None` → resolves to `"django"`.
  Validated at launch against the set of registered theme names; an unknown name raises
  `ImproperlyConfigured` (FR-018, SC-005). CLI may override per-invocation (`--theme-name`,
  parallel to the existing `--theme`).

**Rationale.** Textual's theme system (color variables) and CSS (rules) are *layered, not
competing* — this maps cleanly onto "named selector + custom override" without inventing an
abstraction (Constitution VI). Using `Theme` objects for the palette and `.tcss` for fine
overrides is exactly how Textual intends theming to be composed.

**Alternatives rejected.**
- *Encode the django palette only in a `.tcss` file and keep a single `THEME` key.*
  Rejected (clarify Q chose "named themes + override"): a single file can't offer a
  *selectable* set, and shipping the default as a file the user must point at breaks
  zero-config.
- *A structured palette/token dict in settings mapped onto a theme.* Rejected (clarify
  option C): more config surface to validate (Constitution V) and duplicates Textual's own
  `Theme` schema — a parallel theming abstraction (Constitution VI violation).

---

## D7 — Django-admin visual parity layout (FR-006/006a)

**Decision.** Restyle each screen to the admin's information architecture within terminal
limits, themed by D6:
- **Header bar**: a branded top bar (site title) like the admin's `#header`.
- **Breadcrumb / location**: a line under the header (`Home › App › Model › Object`)
  mirroring the admin breadcrumbs, reusing the `_meta` labels already in use.
- **Changelist**: object-tools row (Add) top-right, the result count + active search/sort
  summary, the fixed-width result table (D1), the filter sidebar (D4) on the right, and the
  pagination region (D5) at the bottom — the admin's changelist anatomy.
- **Change/detail**: fieldset sections with section titles (already present), styled to the
  admin's module/box look; Save / Cancel as the admin's submit-row buttons.
- All colors come from the active theme so the parity is "evokes the admin," not hardcoded.

**Rationale.** Implements the clarified "full look-alike" answer at terminal fidelity using
data the screens already have (`_meta`, fieldsets, changelist) — no new admin calls.

**Alternatives rejected.** Pixel/screenshot reproduction — impossible in a terminal and
explicitly out of scope.

---

## D8 — Edit/save bug triage methodology + suspected defects (FR-012..014, SC-003)

**Decision.** Treat "some model edits not working" as a defined defect class, fixed
test-first:
1. Add a sample model (or extend `Book`/`Author`) whose fields cover the full default
   widget set: `CharField`, `TextField`, `BooleanField`(+nullable), choice field, `FK`,
   `M2M`, `DateField`, `DateTimeField`, `JSONField`, `Integer/DecimalField`, plus
   `null=True`/`blank=True` variants.
2. Write `test_save_matrix.py` that, per field, drives create + edit through `Pilot` and
   asserts (a) the save succeeds, (b) the persisted value equals the input, (c) the
   `LogEntry` matches the web admin. Run it against current code to capture the real
   failures (the matrix is the source of truth for "what's broken").
3. Root-cause in `screens/change.py`. **Suspected defects** to verify against the matrix
   (hypotheses, not yet confirmed):
   - `_gather_data` only emits keys for fields present in `self._widgets`. **M2M
     (`SelectMultiple`)** and any **MultiWidget** (split date/time, etc.) are not handled
     by `_read_widget_value`, so their data is dropped → silent no-op or validation error
     on edit. Likely the core "edit not working" case.
   - `_read_widget_value` for `Select` returns `str(v)`; an FK whose value is unset vs.
     `Select.BLANK` must map to `""` (handled), but **M2M needs a list of pks**, which the
     current single-value path can't produce.
   - `Switch` → `"True"/"False"`: confirm Django's `CheckboxInput.value_from_datadict`
     interprets the rebuilt data dict correctly (unchecked must mean *absent/False*).
   - Date/Datetime `Input` strings must match `DATE_INPUT_FORMATS` / `DATETIME_INPUT_FORMATS`
     or the field widget's expected format; mismatch surfaces as a validation error rather
     than a save.
   - Edit binding: confirm `_build_form(..., obj=self.obj, data=data)` binds `instance=obj`
     so a save **updates** rather than inserts.
4. Fix the minimal cause (extend `_read_widget_value` + `_gather_data` to cover
   multi-value/MultiWidget fields; ensure the rebind passes `instance`), keeping every save
   on the `get_form → is_valid → save_model/save_related → log_*` path (Constitution I/II).

**Rationale.** Without reproducing the failures we'd be guessing; the matrix both finds and
locks them (FR-013 requires a test that fails pre-fix). Routing the fix through the gather
layer (not the admin layer) keeps admin behavior untouched.

**Alternatives rejected.** Patching individual reported fields ad hoc — would leave the
class of multi-value bugs unaddressed and unguarded.

---

## D9 — Mouse always-on; density/mouse settings toggles deferred (Constitution V)

**Decision.** Mouse support is always enabled (Textual default); keyboard parity is
guaranteed (FR-010). Do **not** add `DENSITY` or `MOUSE_ENABLED` settings keys in v2.

**Rationale.** Constitution V: the default answer to "should this be configurable?" is *no*
until a concrete need is shown. Keyboard already works everywhere (so a "disable mouse"
escape hatch has no functional need), Textual lacks a clean public mouse-capture toggle
(adding one risks wrapping the framework — Constitution VI), and density is achievable
today via the `.tcss` override. The clarify option listed these as *optional* ("e.g.
density/mouse"); deferring them keeps the surface minimal. They can be added later under
FR-031 if a real need appears.

**Alternatives rejected.** Adding both toggles speculatively — violates Principle V and
adds validation surface for no demonstrated benefit.

---

## D10 — Preserve all v1 behavior (FR-007/FR-020, SC-007)

**Decision.** No change to querysets, search, filter predicates, ordering, pagination,
form construction, validation, permissions, actions, or audit. v1's full test suite MUST
stay green; the v2 suites are additive. Any v2 change that would alter a v1 assertion is a
bug in v2, not an accepted change.

**Rationale.** v2 is explicitly presentation/interaction/bug-fix scope; SC-007 makes "v1
criteria still pass" a release gate.
