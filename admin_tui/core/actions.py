"""Admin action runner — Constitution I + FR-019 error-path contract.

`_run_action(overlay, request, action_name, queryset)` calls the action
callable that the registered `ModelAdmin` exposes via `get_actions(request)`.

FR-019 obligations (the C1 remediation from /speckit-analyze):
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

The TUI-native bulk actions declared on `TuiAdmin.bulk_actions` are
exercised in Phase 6 (US4). v1 here routes only admin-declared actions.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from django.db.models import QuerySet
    from django.http import HttpRequest

    from admin_tui.options import TuiAdmin


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
    overlay: "TuiAdmin",
    request: "HttpRequest",
) -> dict[str, tuple[Callable, str, str]]:
    """Return the admin-declared actions for `request.user`.

    Mirrors `ModelAdmin.get_actions(request)` exactly — that helper
    already filters by permission, so we don't second-guess it.
    """
    return overlay.model_admin.get_actions(request)


def _run_action(
    overlay: "TuiAdmin",
    request: "HttpRequest",
    action_name: str,
    queryset: "QuerySet",
) -> ActionResult:
    """Run one admin action against `queryset` and capture the outcome.

    See module docstring for the FR-019 control flow.
    """
    actions = overlay.model_admin.get_actions(request)
    if action_name not in actions:
        raise KeyError(
            f"Action {action_name!r} is not available (filtered out by "
            f"ModelAdmin.get_actions for this user)."
        )
    func, _name, _description = actions[action_name]

    # Snapshot the messages list length so we can return ONLY this
    # action's messages (others may have been captured earlier in the
    # session, e.g. by previous actions).
    messages_before = len(request._messages.captured)

    overlay.before_action(request, action_name, queryset)

    try:
        partial_result = func(overlay.model_admin, request, queryset)
    except (KeyboardInterrupt, SystemExit):
        # Surface fatal interrupts upstream.
        raise
    except Exception as exc:
        # Action emitted messages before failing — keep them. Do NOT fire
        # after_action's success branch. Caller MUST NOT route through
        # audit helpers on this path (FR-019).
        return ActionResult(
            messages=list(request._messages.captured[messages_before:]),
            exception=exc,
            partial_result=None,
        )

    # Success path: fire after_action, return captured messages + result.
    overlay.after_action(
        request, action_name, queryset, result=partial_result
    )
    return ActionResult(
        messages=list(request._messages.captured[messages_before:]),
        exception=None,
        partial_result=partial_result,
    )
