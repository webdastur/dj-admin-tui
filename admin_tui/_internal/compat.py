"""Compat scanner — detect genuinely-unreachable admin extensions.

A registered `ModelAdmin` drives the TUI fully with no `tui.py` and no
`TuiAdmin` subclass: the synthesised overlay routes every form through
`get_form`/`get_fieldsets`, saves via `save_model`/`save_related`, and
checks `has_*_permission` — so the standard add/change/delete surface
works even when the admin customises it (Django's own `UserAdmin`, with
its two-step `add_form`/`add_fieldsets` create flow, is supported this
way). We therefore do NOT flag overrides we already replicate from the
declarative surface — `change_view`/`add_view`/`delete_view`, custom
templates, `Media`, etc.

What the terminal genuinely cannot reach is *extra* pages a ModelAdmin
mounts via `get_urls` (a custom report, a password-change view, …). Those
are auxiliary to CRUD, so we surface a single neutral heads-up rather than
asking the operator to reimplement anything.

`scan(admin_site)` returns `{Model: [override_name, ...]}` for every
registered model that mounts such extras. The session caches its own copy
so `IndexScreen` can surface a one-time note the first time the operator
opens an affected model (only when `COMPAT_WARNINGS` is enabled — it is
off by default).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from django.contrib.admin import AdminSite

# Overrides that add admin functionality the terminal cannot render. Kept
# deliberately to the one case that matters — extra views/pages mounted via
# `get_urls` — since everything else in the declarative admin surface is
# already driven by the synthesised overlay.
TARGET_ATTRIBUTES: tuple[str, ...] = ("get_urls",)


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
