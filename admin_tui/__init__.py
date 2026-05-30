"""admin_tui — a terminal UI for the Django admin.

Public surface (FR-030, Constitution Principle V): exactly these names
are public; everything else under `admin_tui.*` is internal and may
change without notice.

    register        — decorator to register a TuiAdmin overlay for a model
    TuiAdmin        — base class for per-model overlays
    tui_site        — process-wide overlay registry singleton
    field_widgets   — process-wide field-widget registry singleton
    AdminTuiApp     — the Textual App subclass; subclass to reskin
"""

from __future__ import annotations

from admin_tui._internal.public_api import _PUBLIC_NAMES
from admin_tui.app import AdminTuiApp
from admin_tui.options import TuiAdmin, register
from admin_tui.sites import tui_site
from admin_tui.widgets import field_widgets

default_app_config = "admin_tui.apps.AdminTuiConfig"

__all__ = list(_PUBLIC_NAMES)

# Surface-freezing invariant: the names we expose MUST exactly match the
# `_PUBLIC_NAMES` tuple. The unit test `tests/unit/test_public_api.py`
# repeats this assertion at test time so a refactor can't drift.
_exported = {"register", "TuiAdmin", "tui_site", "field_widgets", "AdminTuiApp"}
assert _exported == set(_PUBLIC_NAMES), (
    "admin_tui.__init__ exports drifted from _PUBLIC_NAMES"
)
del _exported
