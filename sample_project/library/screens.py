"""Custom Textual screens for the library sample.

- `AuthorStatsScreen` — substituted in for the default `ChangeScreen` via
  `AuthorTui.get_detail_screen(...)`. Exercises the full-screen
  replacement extension slot.
- `LogEntryScreen` — global tool screen registered via
  `tui_site.register_screen("logs", ...)`. Reachable from the index
  via the `g` binding.
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

    from dj_admin_tui._internal.session import TuiSession
    from dj_admin_tui.options import TuiAdmin


class AuthorStatsScreen(Screen):
    """Custom detail Screen for Author — proves get_detail_screen overrides."""

    BINDINGS = [
        Binding("q", "back", "Back", show=True),
        Binding("e", "edit_in_default", "Edit", show=True),
    ]

    DEFAULT_CSS = """
    AuthorStatsScreen #stats-body {
        padding: 2 4;
    }
    """

    def __init__(
        self,
        *,
        session: TuiSession,
        overlay: TuiAdmin,
        request: HttpRequest,
        obj: Any | None = None,
    ) -> None:
        super().__init__()
        self.session = session
        self.overlay = overlay
        self.request = request
        self.obj = obj

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Vertical(id="stats-body"):
            yield Static(f"[b]Author:[/] {self.obj.name}")
            yield Static(f"[dim]Born:[/] {self.obj.born or '?'}")
            book_count = self.obj.books.count()
            yield Static(f"[dim]Books:[/] {book_count}")
            latest = self.obj.books.order_by("-published").first()
            if latest:
                yield Static(
                    f"[dim]Most recent:[/] {latest.title} ({latest.published or 'undated'})"
                )
            else:
                yield Static("[dim]No books on file.[/]")
            yield Static("\n[dim]Press e to switch to the default edit form.[/]")
        yield Footer()

    def action_back(self) -> None:
        self.app.pop_screen()

    def action_edit_in_default(self) -> None:
        from dj_admin_tui.screens.change import ChangeScreen

        self.app.pop_screen()
        self.app.push_screen(
            ChangeScreen(
                session=self.session,
                overlay=self.overlay,
                request=self.request,
                obj=self.obj,
                mode="edit",
            )
        )


class LogEntryScreen(Screen):
    """Global tool screen: recent `LogEntry` rows for the session user."""

    BINDINGS = [Binding("q", "back", "Back", show=True)]

    DEFAULT_CSS = """
    LogEntryScreen #logs-body {
        padding: 1 2;
    }
    LogEntryScreen .log-row {
        height: auto;
    }
    """

    def __init__(self, *, session: TuiSession) -> None:
        super().__init__()
        self.session = session

    def compose(self) -> ComposeResult:
        from django.contrib.admin.models import LogEntry

        yield Header(show_clock=False)
        with VerticalScroll(id="logs-body"):
            yield Static(f"[b]Recent activity[/] — {self.session.user.username}")
            entries = LogEntry.objects.filter(user=self.session.user).order_by("-action_time")[:25]
            count = entries.count()
            if count == 0:
                yield Static("[dim]No log entries.[/]")
            else:
                for entry in entries:
                    label = entry.get_action_flag_display()
                    yield Static(
                        f"{entry.action_time:%Y-%m-%d %H:%M:%S}  "
                        f"[b]{label:<8}[/]  {entry.object_repr}",
                        classes="log-row",
                    )
        yield Footer()

    def action_back(self) -> None:
        self.app.pop_screen()
