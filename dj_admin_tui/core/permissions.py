"""Permission gate — delegates entirely to ModelAdmin's own hooks.

We never introduce a parallel "TUI permission" concept. Every read passes
through `has_view_permission` (or
`has_module_permission` at the index layer), every mutation through the
corresponding `has_*_permission`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from django.contrib.admin import ModelAdmin
    from django.http import HttpRequest


PermissionAction = Literal["view", "add", "change", "delete"]


def _check(
    action: PermissionAction,
    model_admin: ModelAdmin,
    request: HttpRequest,
    obj: Any | None = None,
) -> bool:
    """True iff the admin would let `request.user` perform `action`.

    Routes to `model_admin.has_{action}_permission(request, obj)` exactly
    as the web admin's own permission gate does.
    """
    method = getattr(model_admin, f"has_{action}_permission")
    if action in ("view", "change", "delete"):
        return bool(method(request, obj))
    return bool(method(request))
