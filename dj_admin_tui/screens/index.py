"""IndexScreen — apps → models, scoped by web-admin permissions.

The list is built from `tui_site.models_for(request)`, which already
filters by `has_module_permission` (per app) and `has_view_permission`
(per model) — the same gates the web admin uses for its own index.

Selecting a model row pushes the changelist screen the overlay declares
via `get_changelist_screen(request)` — defaults travel the same path
overlays use.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Container, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import Footer, Header, ListItem, ListView, Static

from dj_admin_tui.core.request import build_request
from dj_admin_tui.sites import tui_site

if TYPE_CHECKING:
    from dj_admin_tui._internal.session import TuiSession


class _ModelListItem(ListItem):
    """ListItem carrying the model it represents, so selection can look it up."""

    def __init__(self, app_label: str, model_name: str, model) -> None:  # type: ignore[no-untyped-def]
        super().__init__(Static(f"{app_label} · {model_name}"))
        self.model = model


class _ToolScreenItem(ListItem):
    """ListItem for a globally-registered tool screen (`tui_site._screens`)."""

    def __init__(self, slug: str, screen_cls: type) -> None:
        super().__init__(Static(f"[b]{slug}[/]"))
        self.slug = slug
        self.screen_cls = screen_cls


class _ToolScreenPickerModal(ModalScreen[type | None]):
    """Lists registered tool screens; dismisses with the chosen screen class."""

    BINDINGS: ClassVar[list[BindingType]] = [Binding("escape", "cancel", "Cancel", show=True)]

    def __init__(self, screens: dict[str, type]) -> None:
        super().__init__()
        self._screens = screens

    def compose(self) -> ComposeResult:
        with Vertical(id="tool-picker"):
            yield Static("[b]Tool screens[/]")
            list_view = ListView(id="tool-list")
            yield list_view

    def on_mount(self) -> None:
        list_view = self.query_one("#tool-list", ListView)
        for slug, screen_cls in self._screens.items():
            list_view.append(_ToolScreenItem(slug, screen_cls))
        list_view.focus()

    def action_cancel(self) -> None:
        self.dismiss(None)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        item = event.item
        if isinstance(item, _ToolScreenItem):
            self.dismiss(item.screen_cls)


class IndexScreen(Screen):
    """The first screen mounted by AdminTuiApp."""

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("q", "quit", "Quit", show=True),
        Binding("?", "show_help", "Help", show=True),
        Binding("g", "tools", "Tools", show=True),
        Binding("enter", "open_model", "Open", show=False),
    ]

    def __init__(self, session: TuiSession) -> None:
        super().__init__()
        self.session = session

    # All styling lives in the shared design system (dj_admin_tui/styles.tcss).

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield Static("Home", id="index-breadcrumb", classes="atui-breadcrumb")
        with Container(id="index-container"):
            yield Static(
                f"Django administration — running as [b]"
                f"{getattr(self.session.user, 'username', '?')}[/]",
                id="index-greeting",
            )
            yield ListView(id="index-list")
        yield Footer()

    def on_mount(self) -> None:
        self._populate()
        self._populate_compat_report()

    def _populate_compat_report(self) -> None:
        """Lazy-fill `session.compat_report` on first mount."""
        if self.session.compat_report:
            return
        from django.contrib import admin as django_admin

        from dj_admin_tui._internal import compat as compat_module
        from dj_admin_tui.conf import _loaded

        if not _loaded.get("COMPAT_WARNINGS", False):
            return
        self.session.compat_report = compat_module.scan(django_admin.site)

    def _populate(self) -> None:
        request = build_request(self.session.user)
        request._tui_session = self.session
        items = tui_site.models_for(request)
        list_view = self.query_one("#index-list", ListView)
        list_view.clear()
        for app_label, model, _overlay in items:
            list_view.append(_ModelListItem(app_label, model._meta.object_name, model))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Enter on a model row → push the configured changelist screen."""
        item = event.item
        if not isinstance(item, _ModelListItem):
            return
        model = item.model
        self._maybe_warn_compat(model)
        request = build_request(self.session.user)
        request._tui_session = self.session
        overlay = tui_site.get_or_synthesize(model)
        screen_cls = self.app.screen_for_changelist(overlay, request)
        self.app.push_screen(screen_cls(session=self.session, overlay=overlay, request=request))

    def _maybe_warn_compat(self, model) -> None:  # type: ignore[no-untyped-def]
        """One-time per-session FYI if `model`'s admin mounts extra pages.

        The model's add/change/delete works normally here — this only flags
        auxiliary views (custom `get_urls`) that have no terminal equivalent.
        """
        if model in self.session.compat_warned:
            return
        overrides = self.session.compat_report.get(model)
        if not overrides:
            return
        self.session.compat_warned.add(model)
        self.app.notify(
            f"{model._meta.verbose_name}: its add/change/delete work here as "
            f"usual. Custom admin pages ({', '.join(overrides)}) aren't "
            f"available in the terminal.",
            title="Heads-up",
            severity="information",
            timeout=8,
        )

    def action_open_model(self) -> None:
        list_view = self.query_one("#index-list", ListView)
        if list_view.highlighted_child is not None:
            # Manually trigger Selected behavior for keyboard Enter.
            list_view.action_select_cursor()

    def action_tools(self) -> None:
        """Open the tool-screen picker. Defined for the `g` binding."""
        screens = dict(tui_site._screens)
        if not screens:
            self.app.notify(
                "No tool screens registered. Use `tui_site.register_screen(...)`.",
                severity="information",
            )
            return

        def _on_pick(screen_cls: type | None) -> None:
            if screen_cls is None:
                return
            # Tool screens take a `session` kwarg; library/screens.py
            # follows this convention.
            try:
                instance = screen_cls(session=self.session)
            except TypeError:
                # Fallback: no-arg constructor.
                instance = screen_cls()
            self.app.push_screen(instance)

        self.app.push_screen(_ToolScreenPickerModal(screens), _on_pick)
