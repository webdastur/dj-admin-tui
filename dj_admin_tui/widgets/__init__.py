"""Field-class → Textual-widget registry + bundled defaults.

Public API: `field_widgets` (the registry singleton, re-exported via
`dj_admin_tui`). Everything else under `dj_admin_tui.widgets.*` is internal.
"""

from __future__ import annotations

# Register all built-in defaults at package-import time.
from dj_admin_tui.widgets import defaults as _defaults  # noqa: F401  (side-effect)
from dj_admin_tui.widgets.registry import field_widgets

__all__ = ["field_widgets"]
