"""Build the synthetic Django HttpRequest used for every admin call.

The TUI never receives a real HTTP request, but `ModelAdmin` methods read
`request.user`, `request.GET`, and `request._messages` (via `message_user`).
A `RequestFactory`-backed request gives us a real `HttpRequest` carrying the
session user and a capturing messages backend.

This is the single choke point through which every permission check and
audit attribution flows.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.test import RequestFactory

from dj_admin_tui.core.messages import _CapturingMessageStorage

if TYPE_CHECKING:
    from django.http import HttpRequest


def build_request(
    user: Any,
    query: dict[str, Any] | None = None,
    *,
    path: str = "/",
) -> HttpRequest:
    """Synthesise an HttpRequest scoped to `user`.

    Args:
        user: A Django user (must be `is_active=True, is_staff=True` —
            enforced at the CLI layer, not here).
        query: Optional GET params, applied to `request.GET`.
        path: The request path; rarely matters but some admin code paths
            read it.

    Returns:
        An `HttpRequest` with `user`, capturing `_messages`, and a marker
        `_tui_session` attribute (set to `None` here; the CLI replaces it
        with the live `TuiSession`).
    """
    request = RequestFactory().get(path, data=query or {})
    request.user = user
    request._messages = _CapturingMessageStorage(request)
    request._tui_session = None
    return request
