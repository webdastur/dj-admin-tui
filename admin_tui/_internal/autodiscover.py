"""Autodiscover `tui.py` modules in every installed app.

Mirrors `django.contrib.admin.autodiscover()`'s behaviour exactly — see
research.md § R10. Each installed app's optional `tui.py` runs at import
and registers overlays via `@register` / `tui_site.register(...)`.
"""

from __future__ import annotations

from django.utils.module_loading import autodiscover_modules


def autodiscover() -> None:
    """Import every installed app's `tui.py` module, if present."""
    autodiscover_modules("tui")
