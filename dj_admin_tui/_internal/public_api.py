"""The frozen public API surface.

`tests/unit/test_public_api.py` asserts that `dj_admin_tui.__all__` equals
`_PUBLIC_NAMES` exactly. Adding a name here requires a justification, a test,
and a docs entry (see docs/api.md).
"""

from __future__ import annotations

#: The complete public surface at v1.0. See docs/api.md.
_PUBLIC_NAMES: tuple[str, ...] = (
    "register",
    "TuiAdmin",
    "tui_site",
    "field_widgets",
    "AdminTuiApp",
)
