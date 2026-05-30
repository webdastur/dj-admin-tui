"""Django AppConfig for admin_tui.

On `ready()`:
  1. Load and validate `ADMIN_TUI` settings (`admin_tui.conf._load()`).
  2. If autodiscovery is enabled, import every installed app's `tui.py`
     via `_internal.autodiscover.autodiscover()`.

The order matters: settings must be loaded first because autodiscovery
respects `ADMIN_TUI["AUTODISCOVER"]`.
"""

from __future__ import annotations

from django.apps import AppConfig


class AdminTuiConfig(AppConfig):
    name = "admin_tui"
    default_auto_field = "django.db.models.BigAutoField"
    verbose_name = "Admin TUI"

    def ready(self) -> None:
        from admin_tui import conf
        from admin_tui._internal import autodiscover

        conf._load()
        if conf._loaded["AUTODISCOVER"]:
            autodiscover.autodiscover()
