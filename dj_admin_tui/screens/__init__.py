"""Built-in Textual screens — `IndexScreen`, `ChangelistScreen`,
`ChangeScreen`, `ActionConfirmScreen`.

Internal: importable, but not part of the public surface. Overlays
substitute their own via `TuiAdmin.get_changelist_screen` /
`get_detail_screen`.

This `__init__` exists so `dj_admin_tui.screens.index` etc. resolve as
submodules; concrete screens are written in their own files.
"""
