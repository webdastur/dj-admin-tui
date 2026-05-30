"""ChangelistScreen — Textual DataTable backed by `ModelAdmin.get_changelist_instance`.

Every state change (search query, filter toggle, sort cycle, paging)
rebuilds the changelist by calling `_build_changelist` again. The
`ChangeList` IS the source of truth — we never recompute filtering or
ordering (Constitution I).

Phase 3 (US1) landed read-only browse. Phase 5 (US3) adds:
  - Space toggles a row's selection (tracked across pagination).
  - `x` opens an action picker. The picker fuses admin-declared
    actions (`ModelAdmin.get_actions(request)` minus the web admin's
    `delete_selected`) with a TUI-managed delete entry.
  - Confirmation goes through `ActionConfirmScreen`, which routes
    admin actions to `_run_action(...)` (FR-019 error path) and the
    TUI delete to `delete_queryset` + `_log_deletion`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import (
    DataTable,
    Footer,
    Header,
    Input,
    ListItem,
    ListView,
    Static,
)

from admin_tui.core.actions import _get_actions
from admin_tui.core.changelist import _build_changelist
from admin_tui.core.request import build_request
from admin_tui.screens.action_confirm import DELETE_SENTINEL, ActionConfirmScreen

if TYPE_CHECKING:
    from django.http import HttpRequest

    from admin_tui._internal.session import TuiSession
    from admin_tui.options import TuiAdmin


SELECTION_COLUMN_KEY = "__selected__"


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


class _ActionPickerItem(ListItem):
    def __init__(self, kind: str, action_name: str, label: str) -> None:
        prefix = {"admin": "", "tui": "[dim]·[/] ", "delete": ""}.get(kind, "")
        super().__init__(Static(f"{prefix}{label}"))
        self.kind = kind
        self.action_name = action_name
        self.action_label = label


class _ActionPickerModal(ModalScreen[tuple[str, str, str] | None]):
    """Lists available actions; dismisses with (kind, action_name, label) or None."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=True),
        Binding("enter", "select", "Select", show=False),
    ]

    DEFAULT_CSS = """
    _ActionPickerModal #action-picker {
        background: $surface;
        border: tall $primary;
        padding: 1 2;
        width: 60;
        height: auto;
        max-height: 80%;
    }
    """

    def __init__(self, actions: list[tuple[str, str, str]]) -> None:
        super().__init__()
        self._actions = actions

    def compose(self) -> ComposeResult:
        with Vertical(id="action-picker"):
            yield Static("[b]Choose an action[/]")
            list_view = ListView(id="action-list")
            yield list_view

    def on_mount(self) -> None:
        list_view = self.query_one("#action-list", ListView)
        for kind, name, label in self._actions:
            list_view.append(_ActionPickerItem(kind, name, label))
        list_view.focus()

    def action_cancel(self) -> None:
        self.dismiss(None)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        item = event.item
        if isinstance(item, _ActionPickerItem):
            self.dismiss((item.kind, item.action_name, item.action_label))


class ChangelistScreen(Screen):
    """Default changelist Screen. Overlays may substitute via
    `TuiAdmin.get_changelist_screen(request)`."""

    BINDINGS = [
        Binding("q", "back", "Back", show=True),
        Binding("/", "search", "Search", show=True),
        Binding("s", "cycle_sort", "Sort", show=True),
        Binding("a", "add", "Add", show=True),
        Binding("space", "toggle_select", "Select", show=True),
        Binding("x", "open_action_picker", "Actions", show=True),
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
        # Selection persists across pagination + filter changes so the
        # operator can build up a selection that spans pages.
        self.selected_pks: set[str] = set()

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
        self._bind_overlay_keys()

    def _bind_overlay_keys(self) -> None:
        """Register the overlay's `key_bindings` dynamically.

        Each entry is `(key, method_name, description)`. We bind the key
        to `row_invoke(method_name)` which dispatches to the overlay's
        method on the focused row.
        """
        for entry in getattr(self.overlay, "key_bindings", []) or []:
            if not entry:
                continue
            if len(entry) >= 3:
                key, method_name, description = entry[0], entry[1], entry[2]
            elif len(entry) == 2:
                key, method_name = entry
                description = method_name
            else:
                continue
            # `bind` evaluates the action string at run time. Quote the
            # method_name as a string parameter.
            self.bind(
                keys=key,
                action=f"row_invoke('{method_name}')",
                description=description,
            )

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
        if self.selected_pks:
            bits.append(f"selected: {len(self.selected_pks)}")
        if q:
            bits.append(f"search: {q!r}")
        sort = self.query.get("o", "")
        if sort:
            bits.append(f"sort: {sort}")
        self.query_one("#changelist-header", Static).update(" · ".join(bits))

    def _refresh_table(self, changelist) -> None:  # type: ignore[no-untyped-def]
        table = self.query_one("#changelist-table", DataTable)
        table.clear(columns=True)

        # Leading selection-indicator column.
        table.add_column(" ", key=SELECTION_COLUMN_KEY, width=2)

        columns = list(self.overlay.get_list_columns(self.request))
        for col in columns:
            table.add_column(self._column_label(col), key=col)

        for obj in changelist.result_list:
            pk = str(obj.pk)
            marker = "✓" if pk in self.selected_pks else " "
            row_values = [marker]
            for col in columns:
                cell = self.overlay.render_cell(self.request, obj, col)
                row_values.append(cell.display)
            table.add_row(*row_values, key=pk)

    def _column_label(self, name: str) -> str:
        try:
            from django.contrib.admin.utils import label_for_field

            return str(
                label_for_field(
                    name,
                    self.overlay.model_admin.model,
                    self.overlay.model_admin,
                )
            )
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
        table = self.query_one("#changelist-table", DataTable)
        if table.cursor_column is None:
            return
        col_index = table.cursor_column
        # Skip the selection-indicator column (index 0) — sorting it makes
        # no sense. The actual sort column is offset by -1.
        if col_index == 0:
            return
        target = str(col_index)  # Django's `o` is 1-based against list_display.
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

    def action_add(self) -> None:
        if not self.overlay.has_add_permission(self.request):
            return
        detail_request = build_request(self.session.user)
        detail_request._tui_session = self.session
        screen_cls = self.app.screen_for_detail(self.overlay, detail_request, None)
        self.app.push_screen(
            screen_cls(
                session=self.session,
                overlay=self.overlay,
                request=detail_request,
                obj=None,
                mode="add",
            )
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

    # ---- multi-select + actions ---------------------------------------

    def action_toggle_select(self) -> None:
        table = self.query_one("#changelist-table", DataTable)
        if table.cursor_row is None:
            return
        row_key, _col_key = table.coordinate_to_cell_key(table.cursor_coordinate)
        pk = row_key.value if row_key is not None else None
        if pk is None:
            return
        if pk in self.selected_pks:
            self.selected_pks.discard(pk)
        else:
            self.selected_pks.add(pk)
        # Just refresh the indicator column + header rather than the whole table.
        self._refresh_selection_indicator(table, pk)
        self._rebuild_header()

    def _rebuild_header(self) -> None:
        changelist = _build_changelist(
            self.overlay.model_admin, self.request, query=self.query
        )
        self._refresh_header(changelist)

    def _refresh_selection_indicator(
        self,
        table: DataTable,
        pk: str,
    ) -> None:
        marker = "✓" if pk in self.selected_pks else " "
        try:
            table.update_cell(pk, SELECTION_COLUMN_KEY, marker)
        except Exception:
            # Cell may not exist if a rebuild happened between key press
            # and this call; safe to swallow.
            pass

    def action_open_action_picker(self) -> None:
        if not self.selected_pks:
            self.app.notify(
                "Select rows with Space first.",
                severity="warning",
            )
            return

        actions = self._available_actions()
        if not actions:
            self.app.notify(
                "No actions available for the current user.",
                severity="warning",
            )
            return

        def _on_pick(result: tuple[str, str, str] | None) -> None:
            if result is None:
                return
            kind, action_name, action_label = result
            self._open_confirm(kind, action_name, action_label)

        self.app.push_screen(_ActionPickerModal(actions), _on_pick)

    def _available_actions(self) -> list[tuple[str, str, str]]:
        """Build the (kind, action_name, label) list shown in the picker.

        Skip the web admin's `delete_selected` (it expects an HTTP
        request/response cycle); offer our own TUI-managed delete instead
        when the user has delete permission. Include the overlay's
        `bulk_actions` as kind="tui" entries.
        """
        out: list[tuple[str, str, str]] = []
        admin_actions = _get_actions(self.overlay, self.request)
        for name, (_func, _action_name, description) in admin_actions.items():
            if name == "delete_selected":
                continue
            out.append(("admin", name, str(description or name)))
        # TUI-native bulk actions declared on the overlay (FR-024).
        for method_name in getattr(self.overlay, "bulk_actions", []) or []:
            label = method_name.replace("_", " ").title()
            out.append(("tui", method_name, label))
        if self.overlay.has_delete_permission(self.request):
            out.append(("delete", DELETE_SENTINEL, "Delete selected"))
        return out

    def _open_confirm(
        self, kind: str, action_name: str, action_label: str
    ) -> None:
        confirm_request = build_request(self.session.user)
        confirm_request._tui_session = self.session
        queryset = self.overlay.model_admin.get_queryset(confirm_request).filter(
            pk__in=self.selected_pks
        )
        self.app.push_screen(
            ActionConfirmScreen(
                session=self.session,
                overlay=self.overlay,
                request=confirm_request,
                action_name=action_name,
                action_label=action_label,
                queryset=queryset,
                kind=kind,  # type: ignore[arg-type]
            )
        )

    def action_row_invoke(self, method_name: str) -> None:
        """Dispatch an overlay's key-bound row action on the focused row.

        Wraps the call in the same FR-019 spirit: any exception is
        surfaced as a Textual notification, the screen stays mounted.
        """
        table = self.query_one("#changelist-table", DataTable)
        if table.cursor_row is None:
            self.app.notify("Move the cursor to a row first.", severity="warning")
            return
        row_key, _col_key = table.coordinate_to_cell_key(table.cursor_coordinate)
        pk = row_key.value if row_key is not None else None
        if pk is None:
            return
        try:
            obj = self.overlay.model_admin.get_queryset(self.request).get(pk=pk)
        except Exception as exc:
            self.app.notify(f"Could not load row: {exc}", severity="error")
            return
        method = getattr(self.overlay, method_name, None)
        if not callable(method):
            self.app.notify(
                f"Overlay method {method_name!r} is not declared.",
                severity="error",
            )
            return
        try:
            method(self.request, obj)
        except Exception as exc:
            self.app.notify(
                f"{type(exc).__name__}: {exc}",
                severity="error",
            )
            return
        self._reset_request_and_rebuild()

    # ---- helpers -------------------------------------------------------

    def _reset_request_and_rebuild(self) -> None:
        self.request = build_request(self.session.user)
        self.request._tui_session = self.session
        self._rebuild()

    def on_screen_resume(self) -> None:
        """Refresh after returning from a detail / action / confirm screen.

        Action runs or deletes may have changed the underlying data; rebuild
        so the operator sees the current state. Clear selections of objects
        that no longer exist."""
        # Drop any selected pks that no longer exist (e.g. after delete).
        if self.selected_pks:
            qs = self.overlay.model_admin.get_queryset(self.request)
            existing = set(
                str(pk) for pk in qs.filter(pk__in=self.selected_pks).values_list(
                    "pk", flat=True
                )
            )
            self.selected_pks &= existing
        self._reset_request_and_rebuild()
