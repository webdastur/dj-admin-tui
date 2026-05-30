"""ChangelistScreen — Textual DataTable backed by `ModelAdmin.get_changelist_instance`.

Every state change (search query, filter toggle, sort cycle, paging)
rebuilds the changelist by calling `_build_changelist` again. The
`ChangeList` IS the source of truth — we never recompute filtering or
ordering (Constitution I).

US1 (Phase 3) lands the read-only path: columns + search + filter + sort +
pagination. US3 (Phase 5) extends this screen with multi-select and
action dispatch.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen, Screen
from textual.widgets import DataTable, Footer, Header, Input, Static

from admin_tui.core.changelist import _build_changelist
from admin_tui.core.request import build_request

if TYPE_CHECKING:
    from django.http import HttpRequest

    from admin_tui._internal.session import TuiSession
    from admin_tui.options import TuiAdmin


class _SearchModal(ModalScreen[str]):
    """Tiny modal that prompts for a search query."""

    BINDINGS = [Binding("escape", "dismiss", "Cancel", show=True)]

    def __init__(self, initial: str = "") -> None:
        super().__init__()
        self._initial = initial

    def compose(self) -> ComposeResult:
        with Container(id="search-modal"):
            yield Static("Search:", id="search-label")
            yield Input(value=self._initial, id="search-input")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value)


class ChangelistScreen(Screen):
    """Default changelist Screen. Overlays may substitute via
    `TuiAdmin.get_changelist_screen(request)`."""

    BINDINGS = [
        Binding("q", "back", "Back", show=True),
        Binding("/", "search", "Search", show=True),
        Binding("s", "cycle_sort", "Sort", show=True),
        Binding("pageup", "page_prev", "PgUp", show=False),
        Binding("pagedown", "page_next", "PgDn", show=False),
        Binding("enter", "open_detail", "Open", show=False),
    ]

    DEFAULT_CSS = """
    ChangelistScreen #changelist-header {
        height: auto;
        padding: 1;
    }
    ChangelistScreen #changelist-table {
        height: 1fr;
    }
    """

    def __init__(
        self,
        *,
        session: "TuiSession",
        overlay: "TuiAdmin",
        request: "HttpRequest",
        query: dict[str, Any] | None = None,
    ) -> None:
        super().__init__()
        self.session = session
        self.overlay = overlay
        self.request = request
        self.query: dict[str, Any] = dict(query or {})

    # ---- mount + render ------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield Static("", id="changelist-header")
        yield DataTable(
            cursor_type="row",
            zebra_stripes=True,
            id="changelist-table",
        )
        yield Footer()

    def on_mount(self) -> None:
        self._rebuild()

    def _rebuild(self) -> None:
        changelist = _build_changelist(
            self.overlay.model_admin, self.request, query=self.query
        )
        self._refresh_header(changelist)
        self._refresh_table(changelist)

    def _refresh_header(self, changelist) -> None:  # type: ignore[no-untyped-def]
        model_name = self.overlay.model_admin.model._meta.verbose_name_plural
        page = getattr(changelist, "page_num", 1)
        per_page = getattr(changelist, "list_per_page", None) or 0
        total = changelist.paginator.count
        q = self.query.get("q", "")
        bits = [
            f"[b]{model_name}[/]",
            f"page {page} (×{per_page})",
            f"total: {total}",
        ]
        if q:
            bits.append(f"search: {q!r}")
        sort = self.query.get("o", "")
        if sort:
            bits.append(f"sort: {sort}")
        self.query_one("#changelist-header", Static).update(" · ".join(bits))

    def _refresh_table(self, changelist) -> None:  # type: ignore[no-untyped-def]
        table = self.query_one("#changelist-table", DataTable)
        table.clear(columns=True)

        columns = list(self.overlay.get_list_columns(self.request))
        for col in columns:
            table.add_column(self._column_label(col), key=col)

        for obj in changelist.result_list:
            row_values = []
            for col in columns:
                cell = self.overlay.render_cell(self.request, obj, col)
                row_values.append(cell.display)
            table.add_row(*row_values, key=str(obj.pk))

    def _column_label(self, name: str) -> str:
        # Mirror admin's label_for_field where possible; fall back to title-case.
        try:
            from django.contrib.admin.utils import label_for_field

            return str(label_for_field(name, self.overlay.model_admin.model,
                                       self.overlay.model_admin))
        except Exception:
            return name.replace("_", " ").title()

    # ---- key actions ---------------------------------------------------

    def action_back(self) -> None:
        self.app.pop_screen()

    def action_page_prev(self) -> None:
        page = int(self.query.get("p", 1))
        if page > 1:
            self.query["p"] = page - 1
            self._reset_request_and_rebuild()

    def action_page_next(self) -> None:
        changelist = _build_changelist(
            self.overlay.model_admin, self.request, query=self.query
        )
        page = getattr(changelist, "page_num", 1)
        if page < changelist.paginator.num_pages:
            self.query["p"] = page + 1
            self._reset_request_and_rebuild()

    def action_cycle_sort(self) -> None:
        """Cycle through asc / desc / unset on the focused column."""
        table = self.query_one("#changelist-table", DataTable)
        if table.cursor_column is None:
            return
        col_index = table.cursor_column
        # Django uses 1-based column index in the `o` param, with leading
        # `-` for descending.
        target = str(col_index + 1)
        current = self.query.get("o", "")
        if current == target:
            self.query["o"] = f"-{target}"
        elif current == f"-{target}":
            self.query.pop("o", None)
        else:
            self.query["o"] = target
        self._reset_request_and_rebuild()

    def action_search(self) -> None:
        def _apply(result: str | None) -> None:
            if result is None:
                return
            stripped = result.strip()
            if stripped:
                self.query["q"] = stripped
            else:
                self.query.pop("q", None)
            self.query.pop("p", None)
            self._reset_request_and_rebuild()

        self.app.push_screen(
            _SearchModal(initial=str(self.query.get("q", ""))),
            _apply,
        )

    def action_open_detail(self) -> None:
        table = self.query_one("#changelist-table", DataTable)
        if table.cursor_row is None:
            return
        row_key, _col_key = table.coordinate_to_cell_key(table.cursor_coordinate)
        pk = row_key.value if row_key is not None else None
        if pk is None:
            return
        try:
            obj = self.overlay.model_admin.get_queryset(self.request).get(pk=pk)
        except Exception:
            return
        detail_request = build_request(self.session.user)
        detail_request._tui_session = self.session
        screen_cls = self.app.screen_for_detail(self.overlay, detail_request, obj)
        self.app.push_screen(
            screen_cls(
                session=self.session,
                overlay=self.overlay,
                request=detail_request,
                obj=obj,
            )
        )

    # ---- helpers -------------------------------------------------------

    def _reset_request_and_rebuild(self) -> None:
        """Rebuild the synthetic request so GET reflects the new query, then refresh.

        Reusing the same HttpRequest works (we re-assign request.GET each
        time) but a fresh one is safer if anything we don't control set
        attributes on the previous one.
        """
        self.request = build_request(self.session.user)
        self.request._tui_session = self.session
        self._rebuild()
