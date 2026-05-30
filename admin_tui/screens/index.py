"""IndexScreen — Phase 3 / T050 will flesh this out.

Phase-2 stub: a minimal Screen that imports cleanly so `AdminTuiApp` can
push it on mount. The real implementation lands in T050.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

if TYPE_CHECKING:
    from admin_tui._internal.session import TuiSession


class IndexScreen(Screen):
    """Placeholder index. Replaced in T050."""

    def __init__(self, session: "TuiSession") -> None:
        super().__init__()
        self.session = session

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(
            "admin_tui — running as "
            f"{getattr(self.session.user, 'username', '?')!r}\n\n"
            "Index screen lands in Phase 3 (T050).",
        )
        yield Footer()
