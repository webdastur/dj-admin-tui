"""IndexScreen — apps → models, scoped by web-admin permissions.

The list is built from `tui_site.models_for(request)`, which already
filters by `has_module_permission` (per app) and `has_view_permission`
(per model) — the same gates the web admin uses for its own index
(Constitution II).

Selecting a model row pushes the changelist screen the overlay declares
via `get_changelist_screen(request)` — defaults travel the same path
overlays use (Constitution IV).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import Footer, Header, ListItem, ListView, Static

from admin_tui.core.request import build_request
from admin_tui.sites import tui_site

if TYPE_CHECKING:
    from admin_tui._internal.session import TuiSession


class _ModelListItem(ListItem):
    """ListItem carrying the model it represents, so selection can look it up."""

    def __init__(self, app_label: str, model_name: str, model) -> None:  # type: ignore[no-untyped-def]
        super().__init__(Static(f"{app_label} · {model_name}"))
        self.model = model


class IndexScreen(Screen):
    """The first screen mounted by AdminTuiApp."""

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("?", "show_help", "Help", show=True),
        Binding("enter", "open_model", "Open", show=False),
    ]

    def __init__(self, session: "TuiSession") -> None:
        super().__init__()
        self.session = session

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Container(id="index-container"):
            yield Static(
                f"admin_tui — running as [b]"
                f"{getattr(self.session.user, 'username', '?')}[/]",
                id="index-greeting",
            )
            yield ListView(id="index-list")
        yield Footer()

    def on_mount(self) -> None:
        self._populate()

    def _populate(self) -> None:
        request = build_request(self.session.user)
        request._tui_session = self.session
        items = tui_site.models_for(request)
        list_view = self.query_one("#index-list", ListView)
        list_view.clear()
        for app_label, model, _overlay in items:
            list_view.append(
                _ModelListItem(app_label, model._meta.object_name, model)
            )

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Enter on a model row → push the configured changelist screen."""
        item = event.item
        if not isinstance(item, _ModelListItem):
            return
        model = item.model
        request = build_request(self.session.user)
        request._tui_session = self.session
        overlay = tui_site.get_or_synthesize(model)
        screen_cls = self.app.screen_for_changelist(overlay, request)
        self.app.push_screen(
            screen_cls(session=self.session, overlay=overlay, request=request)
        )

    def action_open_model(self) -> None:
        list_view = self.query_one("#index-list", ListView)
        if list_view.highlighted_child is not None:
            # Manually trigger Selected behavior for keyboard Enter.
            list_view.action_select_cursor()
