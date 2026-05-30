"""The frozen public API surface (FR-030, Constitution Principle V).

`tests/unit/test_public_api.py` asserts that `admin_tui.__all__` equals
`_PUBLIC_NAMES` exactly. Adding a name here requires the justification +
test + docs entry mandated by FR-031.
"""

from __future__ import annotations

#: The complete public surface at v1.0. See specs/.../contracts/public-api.md.
_PUBLIC_NAMES: tuple[str, ...] = (
    "register",
    "TuiAdmin",
    "tui_site",
    "field_widgets",
    "AdminTuiApp",
)
