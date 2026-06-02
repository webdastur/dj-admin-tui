"""Admin action runner — reuse the admin's actions + an error-path contract.

`_run_action(overlay, request, action_name, queryset)` calls the action
callable that the registered `ModelAdmin` exposes via `get_actions(request)`.

Error-path obligations:
  * `before_action(...)` fires unconditionally before the action call.
  * The action call is wrapped in try/except (Exception, not BaseException
    — KeyboardInterrupt/SystemExit propagate).
  * `request._messages.captured` is snapshotted around the call so we can
    surface ONLY this action's messages (some actions message-then-fail).
  * On success, `after_action(..., result=...)` fires.
  * On exception, `after_action`'s success path does NOT fire and the
    caller will NOT route the result through audit helpers (no LogEntry
    claims success for failed work).
  * Returns an `ActionResult` with `messages`, `exception`, and
    `partial_result`. The screen surfaces messages as notifications and
    routes exceptions to a recoverable error display.

This routes only admin-declared actions.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from django.db.models import QuerySet
    from django.http import HttpRequest

    from dj_admin_tui.options import TuiAdmin


@dataclass(frozen=True)
class ActionResult:
    """Outcome of a single action run.

    `messages` is the slice of `request._messages.captured` that this
    action emitted. `exception` is the uncaught Exception subclass if the
    action raised; `partial_result` is the action's return value on
    success (or `None` on failure).
    """

    messages: list[tuple[int, str, str]] = field(default_factory=list)
    exception: BaseException | None = None
    partial_result: Any = None

    @property
    def succeeded(self) -> bool:
        return self.exception is None


def _get_actions(
    overlay: TuiAdmin,
    request: HttpRequest,
) -> dict[str, tuple[Callable, str, str]]:
    """Return the admin-declared actions for `request.user`.

    Mirrors `ModelAdmin.get_actions(request)` exactly — that helper
    already filters by permission, so we don't second-guess it.
    """
    return overlay.model_admin.get_actions(request)


def _run_action(
    overlay: TuiAdmin,
    request: HttpRequest,
    action_name: str,
    queryset: QuerySet,
) -> ActionResult:
    """Run one admin action against `queryset` and capture the outcome.

    See module docstring for the control flow.
    """
    actions = overlay.model_admin.get_actions(request)
    if action_name not in actions:
        raise KeyError(
            f"Action {action_name!r} is not available (filtered out by "
            f"ModelAdmin.get_actions for this user)."
        )
    func, _name, _description = actions[action_name]

    return _dispatch_action(
        overlay=overlay,
        request=request,
        action_name=action_name,
        queryset=queryset,
        call=lambda: func(overlay.model_admin, request, queryset),
    )


def _run_tui_action(
    overlay: TuiAdmin,
    request: HttpRequest,
    method_name: str,
    queryset: QuerySet,
) -> ActionResult:
    """Run a TUI-native bulk action declared on the overlay.

    Same control flow as `_run_action`, but the callable is an overlay
    method rather than an admin-registered action.
    """
    method = getattr(overlay, method_name, None)
    if not callable(method):
        raise KeyError(f"TUI-native bulk action {method_name!r} is not declared on this overlay.")

    return _dispatch_action(
        overlay=overlay,
        request=request,
        action_name=method_name,
        queryset=queryset,
        call=lambda: method(request, queryset),
    )


def _dispatch_action(
    *,
    overlay: TuiAdmin,
    request: HttpRequest,
    action_name: str,
    queryset: QuerySet,
    call: Callable[[], Any],
) -> ActionResult:
    """Shared control flow for admin + TUI-native action dispatch.

    Snapshots `request._messages.captured` before/after; fires
    `before_action` unconditionally; fires `after_action` ONLY on the
    no-exception branch; re-raises KeyboardInterrupt/SystemExit.
    """
    messages_before = len(request._messages.captured)
    overlay.before_action(request, action_name, queryset)

    try:
        partial_result = call()
    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception as exc:
        return ActionResult(
            messages=list(request._messages.captured[messages_before:]),
            exception=exc,
            partial_result=None,
        )

    overlay.after_action(request, action_name, queryset, result=partial_result)
    return ActionResult(
        messages=list(request._messages.captured[messages_before:]),
        exception=None,
        partial_result=partial_result,
    )
