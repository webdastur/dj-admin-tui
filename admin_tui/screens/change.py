"""ChangeScreen — single-object detail view.

Phase 3 (US1) lands the read-only mode: fieldsets per
`ModelAdmin.get_fieldsets(request, obj)`, fields rendered as `name: value`
text. Phase 4 (US2) extends this Screen with create + edit modes using
the widget registry to render input controls and `form.is_valid()` for
validation (Constitution I).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

if TYPE_CHECKING:
    from django.http import HttpRequest

    from admin_tui._internal.session import TuiSession
    from admin_tui.options import TuiAdmin


class ChangeScreen(Screen):
    """Read-only detail view (US1). US2 extends with create + edit."""

    BINDINGS = [
        Binding("q", "back", "Back", show=True),
    ]

    DEFAULT_CSS = """
    ChangeScreen #detail-body {
        height: 1fr;
        padding: 1 2;
    }
    ChangeScreen .field-row {
        height: auto;
        padding: 0 0 1 0;
    }
    """

    def __init__(
        self,
        *,
        session: "TuiSession",
        overlay: "TuiAdmin",
        request: "HttpRequest",
        obj: Any | None = None,
    ) -> None:
        super().__init__()
        self.session = session
        self.overlay = overlay
        self.request = request
        self.obj = obj

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with VerticalScroll(id="detail-body"):
            yield Static(
                self._heading(),
                id="detail-heading",
            )
            for set_name, set_body in self._fieldsets():
                with Vertical(classes="fieldset"):
                    if set_name:
                        yield Static(f"[b]{set_name}[/]", classes="fieldset-name")
                    for field_name in set_body.get("fields", []):
                        yield Static(
                            self._format_field(field_name),
                            classes="field-row",
                        )
        yield Footer()

    # ---- helpers -------------------------------------------------------

    def _heading(self) -> str:
        verbose = self.overlay.model_admin.model._meta.verbose_name
        if self.obj is None:
            return f"[b]New {verbose}[/]"
        return f"[b]{verbose}[/]: {self.obj}"

    def _fieldsets(self) -> list[tuple[str | None, dict[str, Any]]]:
        """Return the fieldsets the admin would render."""
        if self.overlay.detail_fieldsets is not None:
            raw = self.overlay.detail_fieldsets
        else:
            raw = self.overlay.model_admin.get_fieldsets(self.request, self.obj)
        out: list[tuple[str | None, dict[str, Any]]] = []
        for name, body in raw:
            # body is a dict with at least {"fields": (...)}.
            if isinstance(body, dict):
                out.append((name, body))
            else:
                out.append((name, {"fields": list(body)}))
        return out

    def _format_field(self, field_name: str | tuple[str, ...]) -> str:
        if isinstance(field_name, (list, tuple)):
            # Admin fieldsets can group multiple fields per line; show
            # them flat for the TUI.
            return " · ".join(self._format_field(f) for f in field_name)

        if self.obj is None:
            return f"{field_name}: —"

        value = getattr(self.obj, field_name, None)
        if value is None:
            display = "—"
        else:
            display = str(value)
        return f"[dim]{field_name}:[/] {display}"

    # ---- actions -------------------------------------------------------

    def action_back(self) -> None:
        self.app.pop_screen()
