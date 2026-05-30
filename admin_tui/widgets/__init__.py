"""Field-class → Textual-widget registry + bundled defaults.

Public API: `field_widgets` (the registry singleton, re-exported via
`admin_tui`). Everything else under `admin_tui.widgets.*` is internal.
"""

from __future__ import annotations

from admin_tui.widgets.registry import field_widgets

# Register all built-in defaults at package-import time.
from admin_tui.widgets import defaults as _defaults  # noqa: F401  (side-effect)

__all__ = ["field_widgets"]
