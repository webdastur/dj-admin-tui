"""Compat scanner — detect ModelAdmin overrides we cannot honour (R16).

The web admin lets users override `change_view`, `get_urls`, custom
templates, JS, etc. None of those translate to the terminal. The TUI
covers the standard declarative admin surface; non-standard overrides
are documented at first-access via a one-time notification per model
(per spec § Edge Cases).

`scan(admin_site)` returns `{Model: [override_name, ...]}` for every
registered model that overrides any of the targeted attributes. The
session caches its own copy so `IndexScreen` can surface a notification
the first time the operator opens an affected model.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from django.contrib.admin import AdminSite

# Attributes / methods whose customisation indicates a web-only override
# the TUI doesn't honour. The set is intentionally narrow — we don't
# flag every override, just the ones operators ask about.
TARGET_ATTRIBUTES: tuple[str, ...] = (
    "change_view",
    "add_view",
    "delete_view",
    "history_view",
    "get_urls",
    "change_form_template",
    "change_list_template",
    "add_form_template",
    "delete_confirmation_template",
    "Media",
)


def scan(admin_site: "AdminSite") -> dict[Any, list[str]]:
    """Walk the admin site and report customised TARGET_ATTRIBUTES."""
    from django.contrib.admin import ModelAdmin

    report: dict[Any, list[str]] = {}
    for model, model_admin in admin_site._registry.items():
        overrides: list[str] = []
        for attr in TARGET_ATTRIBUTES:
            if _is_overridden(model_admin, attr, base_cls=ModelAdmin):
                overrides.append(attr)
        if overrides:
            report[model] = overrides
    return report


def _is_overridden(
    model_admin: Any,
    attr: str,
    *,
    base_cls: type,
) -> bool:
    """True if `attr` was redefined on the subclass vs. the base ModelAdmin."""
    sub_value = getattr(type(model_admin), attr, None)
    base_value = getattr(base_cls, attr, None)
    return sub_value is not base_value and sub_value is not None
