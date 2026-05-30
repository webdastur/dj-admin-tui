<!-- SPECKIT START -->
The active feature is the **v2 UI redesign**. Read its plan at
[specs/002-ui-redesign-django-parity/plan.md](specs/002-ui-redesign-django-parity/plan.md).
It is a presentation/interaction/bug-fix pass over the completed v1 core
([specs/001-admin-tui-mvp/plan.md](specs/001-admin-tui-mvp/plan.md)) and MUST NOT change
any v1 data behavior (result sets, permissions, validation, saves, audit).

v2 companion artifacts (same folder):
- `spec.md` — feature spec + `## Clarifications` (full look-alike; named themes + override;
  footer cell-preview; single-click focus / double-click open; horizontal-scroll layout).
- `research.md` — locked decisions D1–D10 (layout/truncation, footer preview, mouse model,
  filter sidebar, theming, edit-save bug triage, deferred toggles).
- `data-model.md` — in-memory view-state (ColumnSpec, CellPreview, FilterPanelState,
  AppearanceConfig, SaveData); no persistent storage.
- `contracts/` — `settings.md` (new `THEME_NAME` key), `interaction.md` (keymap + mouse map
  + layout), `theming.md` (bundled themes + `.tcss` precedence).
- `quickstart.md` — theming-via-settings + mouse walkthrough (delta over v1).

Key v2 facts: the changelist glitch is Textual `DataTable` content-auto-sizing +
cursor auto-scroll — fix with selection-independent fixed-width columns + pre-truncation
(`admin_tui/widgets/layout.py`). The edit bug is multi-value/MultiWidget data being dropped
in `screens/change.py` `_gather_data`/`_read_widget_value`. Theming uses Textual `Theme`
objects (`admin_tui/themes/`) + the existing `.tcss` override, layered.

Project principles live in `.specify/memory/constitution.md` (v1.0.0); the plan's
Constitution Check maps each principle to the design choice that satisfies it. Reuse
Django's admin internals; never reimplement them.
<!-- SPECKIT END -->
