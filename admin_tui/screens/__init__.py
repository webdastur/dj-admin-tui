"""Built-in Textual screens — `IndexScreen`, `ChangelistScreen`,
`ChangeScreen`, `ActionConfirmScreen`.

Internal: importable, but not part of the 6-name public surface. Overlays
substitute their own via `TuiAdmin.get_changelist_screen` /
`get_detail_screen` (Constitution IV / VI).

Phase 3 (US1) lands `IndexScreen` and `ChangelistScreen`; Phase 3 also
gives `ChangeScreen` its read-only mode. Phase 4 (US2) extends
`ChangeScreen` with create/edit. Phase 5 (US3) adds `ActionConfirmScreen`
and the multi-select wiring on `ChangelistScreen`.

This `__init__` exists so `admin_tui.screens.index` etc. resolve as
submodules; concrete screens are written in their own files.
"""
