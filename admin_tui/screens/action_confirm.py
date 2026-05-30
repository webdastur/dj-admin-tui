"""ActionConfirmScreen — Yes/No confirmation for actions and delete.

Shown after the operator picks an action from the changelist's action
picker. Lists the action name, selected count, first 5 object reprs,
and Yes / No bindings. On confirm:

  - For a regular admin action: call `_run_action(...)`; surface captured
    messages as Textual notifications; on exception, show an error
    notification + a recoverable "Back" state.
  - For the TUI-managed delete: iterate `queryset` calling
    `_log_deletion` BEFORE the actual delete (so `str(obj)` resolves),
    then `model_admin.delete_queryset(request, queryset)`.

The delete path is separate from `delete_selected` because the web
admin's `delete_selected` action returns an HttpResponse for its
confirmation page; we provide the same audit-correct behaviour in the
terminal without that two-step web flow.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Static

from admin_tui.core.actions import _run_action, _run_tui_action
from admin_tui.core.audit import _log_deletions

if TYPE_CHECKING:
    from django.db.models import QuerySet
    from django.http import HttpRequest

    from admin_tui._internal.session import TuiSession
    from admin_tui.options import TuiAdmin


# Sentinel action name for the TUI-managed delete path.
DELETE_SENTINEL = "_admin_tui_delete"

ActionKind = Literal["admin", "tui", "delete"]


class ActionConfirmScreen(Screen):
    """Confirms an action + dispatches it. Pop back to the changelist on Yes/No."""

    BINDINGS = [
        Binding("y", "confirm", "Yes", show=True),
        Binding("n", "cancel", "No", show=True),
        Binding("escape", "cancel", "Cancel", show=False),
    ]

    # All styling lives in the shared design system (admin_tui/styles.tcss).

    def __init__(
        self,
        *,
        session: "TuiSession",
        overlay: "TuiAdmin",
        request: "HttpRequest",
        action_name: str,
        action_label: str,
        queryset: "QuerySet",
        kind: ActionKind = "admin",
    ) -> None:
        super().__init__()
        self.session = session
        self.overlay = overlay
        self.request = request
        self.action_name = action_name
        self.action_label = action_label
        self.queryset = queryset
        # Sentinel action name takes precedence — it routes to the delete
        # path regardless of `kind` passed in.
        if action_name == DELETE_SENTINEL:
            kind = "delete"
        self.kind: ActionKind = kind
        self._error_message: str | None = None

    # ---- compose -----------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Vertical(id="confirm-body"):
            yield Static(self._title(), id="confirm-title")
            yield Static(self._summary())
            yield Static(self._preview(), classes="preview-list")
            yield Static("", id="error-area", classes="error")
            with Horizontal(id="confirm-buttons"):
                yes_classes = (
                    "atui-btn atui-btn-danger"
                    if self.kind == "delete"
                    else "atui-btn atui-btn-primary"
                )
                yes_label = "Yes, I'm sure" if self.kind == "delete" else "Yes"
                no_label = "No, take me back" if self.kind == "delete" else "No"
                yield Button(yes_label, id="yes-button", classes=yes_classes)
                yield Button(no_label, id="no-button",
                             classes="atui-btn atui-btn-default")
        yield Footer()

    # ---- text helpers ------------------------------------------------

    def _title(self) -> str:
        if self.kind == "delete":
            return "Delete"
        kind_label = "TUI action" if self.kind == "tui" else "Run action"
        return f"{kind_label}: {self.action_label}"

    def _summary(self) -> str:
        verbose = self.overlay.model_admin.model._meta.verbose_name_plural
        count = self.queryset.count()
        if self.kind == "delete":
            return (
                f"Are you sure you want to delete the {count} selected "
                f"{verbose}? All of the following will be deleted:"
            )
        return f"{self.action_label} will run on {count} {verbose}:"

    def _preview(self) -> str:
        sample = list(self.queryset[:5])
        lines = [f"• {obj}" for obj in sample]
        remainder = self.queryset.count() - len(sample)
        if remainder > 0:
            lines.append(f"• … and {remainder} more")
        return "\n".join(lines) or "(empty selection)"

    # ---- actions -----------------------------------------------------

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "yes-button":
            self.action_confirm()
        elif event.button.id == "no-button":
            self.action_cancel()

    def action_confirm(self) -> None:
        if self.kind == "delete":
            self._do_delete()
        else:
            self._do_action()

    def action_cancel(self) -> None:
        self.app.pop_screen()

    # ---- action dispatch --------------------------------------------

    def _do_action(self) -> None:
        if self.kind == "tui":
            result = _run_tui_action(
                self.overlay, self.request, self.action_name, self.queryset
            )
        else:
            result = _run_action(
                self.overlay, self.request, self.action_name, self.queryset
            )

        # Surface captured messages as notifications. Map Django message
        # levels to Textual notify severities.
        from django.contrib.messages import constants as message_constants

        severity_for = {
            message_constants.DEBUG: "information",
            message_constants.INFO: "information",
            message_constants.SUCCESS: "information",
            message_constants.WARNING: "warning",
            message_constants.ERROR: "error",
        }
        for level, message, _tags in result.messages:
            self.app.notify(
                message,
                severity=severity_for.get(level, "information"),
            )

        if result.exception is not None:
            # FR-019 recoverable state: stay on this screen, show the
            # error inline, restore the "Back" affordance.
            self._show_error(
                f"{type(result.exception).__name__}: {result.exception}"
            )
            return

        self.app.pop_screen()

    def _do_delete(self) -> None:
        if not self.overlay.has_delete_permission(self.request):
            self._show_error("You do not have permission to delete these records.")
            return

        verbose = self.overlay.model_admin.model._meta.verbose_name_plural
        try:
            count = self.queryset.count()
            # Audit BEFORE delete so `str(obj)` is resolvable (per-object
            # reprs are captured by Django's log_deletions before the rows
            # are removed).
            _log_deletions(self.overlay.model_admin, self.request, self.queryset)
            self.overlay.model_admin.delete_queryset(self.request, self.queryset)
        except Exception as exc:
            self._show_error(f"{type(exc).__name__}: {exc}")
            return

        self.app.notify(
            f"Deleted {count} {verbose}.",
            severity="information",
        )
        self.app.pop_screen()

    # ---- error display ---------------------------------------------

    def _show_error(self, text: str) -> None:
        target = self.query_one("#error-area", Static)
        target.update(text)
        self.app.notify(text, severity="error")
