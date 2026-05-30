"""ChangelistScreen — Textual DataTable backed by `ModelAdmin.get_changelist_instance`.

Every state change (search query, filter toggle, sort cycle, paging) rebuilds the
changelist by calling `_build_changelist` again. The `ChangeList` IS the source of
truth — we never recompute filtering or ordering (Constitution I).

v2 (UI redesign) layers presentation + interaction over the v1 behavior:
  - Columns get **fixed, selection-independent widths** and every cell is
    **pre-truncated** (`admin_tui.widgets.layout`), killing the v1 glitch where
    DataTable auto-sized columns and auto-scrolled to the cursor cell (FR-001/002).
  - A fixed footer bar previews the focused row's full (untruncated) values with
    no reflow (FR-003).
  - A Django-style filter sidebar (`admin_tui.widgets.filters`) renders the admin's
    own `list_filter` choices (FR-004).
  - Object-tools (Add) + pagination controls are clickable Buttons (FR-004/008).
  - Mouse: single click focuses a row, clicking the focused row / Enter opens it,
    a click on the checkbox column toggles selection, a header click sorts (FR-008).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qsl, urlparse

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.coordinate import Coordinate
from textual.screen import ModalScreen, Screen
from textual.widgets import (
    Button,
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
from admin_tui.widgets.filters import FilterSidebar, extract_filter_groups
from admin_tui.widgets.layout import (
    SELECTION_WIDTH,
    compute_column_widths,
    sanitize_cell,
    truncate_cell,
)

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

    # All styling lives in the shared design system (admin_tui/styles.tcss).

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
        self.query_params: dict[str, Any] = dict(query or {})
        # Selection persists across pagination + filter changes so the
        # operator can build up a selection that spans pages.
        self.selected_pks: set[str] = set()
        # Per-rebuild caches (selection-independent).
        self._specs: list = []
        self._full_cells: dict[str, list[tuple[str, str]]] = {}
        # Sort state mirrored from Django (controlled by ModelAdmin: `ordering`,
        # `sortable_by`, `admin_order_field`). Keys are table column indices.
        self._ordering_cols: dict[int, str] = {}
        self._sortable_positions: set[int] = set()
        # Column under the pointer at the last mouse-down — lets us tell a
        # mouse click on the checkbox column apart from a keyboard Enter when
        # a RowSelected fires. `None` means "no recent mouse activation".
        self._down_column: int | None = None

    # ---- mount + render ------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield Static("", id="changelist-breadcrumb", classes="atui-breadcrumb")
        with Horizontal(id="object-tools"):
            if self.overlay.model_admin.get_search_fields(self.request):
                yield Input(placeholder="Search…", id="search-bar", compact=True)
            yield Static(id="toolbar-spacer", classes="atui-spacer")
            yield Button("+ Add", id="add-button", classes="atui-btn atui-btn-primary")
        yield Static("", id="changelist-header")
        with Horizontal(id="changelist-body"):
            yield DataTable(
                cursor_type="row",
                zebra_stripes=True,
                id="changelist-table",
            )
            yield FilterSidebar(id="filter-sidebar")
        with Horizontal(id="pagination"):
            yield Button("‹ Prev", id="prev-button", classes="atui-btn-link")
            yield Static("", id="page-indicator")
            yield Button("Next ›", id="next-button", classes="atui-btn-link")
        yield Static("", id="cell-preview")
        yield Footer()

    def on_mount(self) -> None:
        self._refresh_breadcrumb()
        # Hide the Add affordance when the user can't add.
        if not self.overlay.has_add_permission(self.request):
            self.query_one("#add-button", Button).display = False
        # Reflect any active search in the persistent search bar.
        q = str(self.query_params.get("q", "") or "")
        if q:
            search_bar = self._search_bar()
            if search_bar is not None:
                search_bar.value = q
        self._rebuild()
        # Focus the table AFTER the initial render so the search bar (which is
        # earlier in the DOM) can't keep the focus — arrow keys must drive the
        # table from the start.
        self.call_after_refresh(self._focus_table)

    def _focus_table(self) -> None:
        try:
            self.query_one("#changelist-table", DataTable).focus()
        except Exception:
            pass

    def _search_bar(self) -> Input | None:
        try:
            return self.query_one("#search-bar", Input)
        except Exception:
            return None

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "search-bar":
            return
        stripped = event.value.strip()
        if stripped:
            self.query_params["q"] = stripped
        else:
            self.query_params.pop("q", None)
        self.query_params.pop("p", None)
        self._reset_request_and_rebuild()
        # Return focus to the table so the operator can navigate results.
        self._focus_table()

    def _refresh_breadcrumb(self) -> None:
        meta = self.overlay.model_admin.model._meta
        app_label = meta.app_config.verbose_name if meta.app_config else meta.app_label
        crumb = f"Home › {app_label} › {meta.verbose_name_plural}"
        self.query_one("#changelist-breadcrumb", Static).update(crumb)

    def on_mouse_down(self, event) -> None:  # type: ignore[no-untyped-def]
        """Record the column under the pointer so a click on the focused row's
        checkbox can be told apart from a keyboard Enter (FR-008a)."""
        meta = getattr(event.style, "meta", {}) or {}
        if "row" in meta and "column" in meta:
            self._down_column = meta["column"]
        else:
            self._down_column = None

    def on_click(self, event) -> None:  # type: ignore[no-untyped-def]
        """Mouse: a click on the checkbox column of a (non-focused) row toggles
        its selection. Body clicks just move the cursor (focus); the focused-row
        click is handled by RowSelected → open (FR-008a)."""
        meta = getattr(event.style, "meta", {}) or {}
        self._down_column = None
        if "row" not in meta or "column" not in meta:
            return
        row_index = meta["row"]
        col_index = meta["column"]
        if row_index < 0 or col_index != 0:
            return
        self._toggle_at_row_index(row_index)
        event.stop()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Activate a row. Fired by Enter (keyboard) or clicking the focused row
        (mouse). A mouse click on the checkbox column toggles selection instead
        of opening (FR-008a)."""
        down_column = self._down_column
        self._down_column = None
        if down_column == 0:
            pk = event.row_key.value if event.row_key is not None else None
            if pk is not None:
                self._toggle_select_pk(str(pk))
            return
        self.action_open_detail()

    def _toggle_at_row_index(self, row_index: int) -> None:
        table = self.query_one("#changelist-table", DataTable)
        try:
            row_key, _ = table.coordinate_to_cell_key(Coordinate(row_index, 0))
        except Exception:
            return
        pk = row_key.value if row_key is not None else None
        if pk is not None:
            self._toggle_select_pk(str(pk))

    def on_data_table_row_highlighted(
        self, event: DataTable.RowHighlighted
    ) -> None:
        """Update the footer cell-preview when the cursor moves (FR-003)."""
        pk = event.row_key.value if event.row_key is not None else None
        self._update_preview(None if pk is None else str(pk))

    def on_data_table_header_selected(
        self, event: DataTable.HeaderSelected
    ) -> None:
        """Mouse: clicking a column header sorts by it (mirrors `s`). Only the
        columns the ModelAdmin marks sortable respond (Django parity)."""
        col_index = event.column_index
        if col_index == 0:  # selection column — not sortable
            return
        if col_index not in self._sortable_positions:
            self.app.notify(
                "This column is not sortable.",
                severity="information",
                timeout=3,
            )
            return
        self._sort_by_column_index(col_index)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id
        if bid == "add-button":
            self.action_add()
        elif bid == "prev-button":
            self.action_page_prev()
        elif bid == "next-button":
            self.action_page_next()

    def on_filter_sidebar_filter_chosen(
        self, event: FilterSidebar.FilterChosen
    ) -> None:
        """Apply Django's own filter query string (Constitution I / FR-004)."""
        parsed = dict(parse_qsl(urlparse(event.query_string).query))
        self.query_params = parsed
        self.query_params.pop("p", None)
        self._reset_request_and_rebuild()

    def on_key(self, event) -> None:  # type: ignore[no-untyped-def]
        """Dispatch overlay-declared `key_bindings` from FR-024.

        Default screen BINDINGS take precedence so an overlay cannot accidentally
        shadow `q`, `/`, `s`, `a`, Space, `x`, PgUp/PgDn, or Enter.
        """
        reserved_keys = {b.key for b in self.BINDINGS}
        if event.key in reserved_keys:
            return
        for entry in getattr(self.overlay, "key_bindings", []) or []:
            if len(entry) < 2:
                continue
            key, method_name = entry[0], entry[1]
            if event.key != key:
                continue
            if not hasattr(self.overlay, method_name):
                continue
            event.stop()
            self.action_row_invoke(method_name)
            return

    def _rebuild(self) -> None:
        # Any of these can hit the DB (missing table, permission error, broken
        # ModelAdmin method, …). A failure MUST surface as a notification and
        # leave the operator on a usable screen — never crash the app.
        try:
            changelist = _build_changelist(
                self.overlay.model_admin, self.request, query=self.query_params
            )
            self._refresh_header(changelist)
            self._refresh_table(changelist)
            self._refresh_filters(changelist)
        except Exception as exc:  # noqa: BLE001 — last-resort UI guard
            self._notify_error("Could not load this list", exc)

    def _notify_error(self, context: str, exc: Exception) -> None:
        """Surface an error as a Textual notification instead of crashing."""
        self.app.notify(
            f"{context}: {type(exc).__name__}: {exc}",
            title="Error",
            severity="error",
            timeout=10,
        )

    def _refresh_header(self, changelist) -> None:  # type: ignore[no-untyped-def]
        model_name = self.overlay.model_admin.model._meta.verbose_name_plural
        page = getattr(changelist, "page_num", 1)
        per_page = getattr(changelist, "list_per_page", None) or 0
        total = changelist.paginator.count
        num_pages = changelist.paginator.num_pages
        q = self.query_params.get("q", "")
        bits = [
            f"[b]{model_name}[/]",
            f"{total} result{'s' if total != 1 else ''} (×{per_page}/page)",
        ]
        if self.selected_pks:
            bits.append(f"selected: {len(self.selected_pks)}")
        if q:
            bits.append(f"search: {q!r}")
        sort_label = self._sort_label(changelist)
        if sort_label:
            bits.append(sort_label)
        self.query_one("#changelist-header", Static).update(" · ".join(bits))
        self.query_one("#page-indicator", Static).update(
            f"page {page} / {num_pages}"
        )

    def _refresh_table(self, changelist) -> None:  # type: ignore[no-untyped-def]
        table = self.query_one("#changelist-table", DataTable)
        table.clear(columns=True)

        columns = list(self.overlay.get_list_columns(self.request))
        objs = list(changelist.result_list)

        # Compute the full (sanitized, untruncated) display per cell ONCE; reuse
        # for width computation, the footer preview, and the truncated row.
        full_rows: list[dict[str, str]] = []
        self._full_cells = {}
        for obj in objs:
            pk = str(obj.pk)
            cells: dict[str, str] = {}
            labelled: list[tuple[str, str]] = []
            for col in columns:
                disp = sanitize_cell(
                    self.overlay.render_cell(self.request, obj, col).display
                )
                cells[col] = disp
                labelled.append((self._column_label(col), disp))
            full_rows.append(cells)
            self._full_cells[pk] = labelled

        layout_cols = [(col, self._column_label(col)) for col in columns]
        self._specs = compute_column_widths(layout_cols, full_rows)

        # Sort state straight from Django (reflects ModelAdmin.ordering default,
        # sortable_by, and admin_order_field). Keys are 1-based against the
        # user's list_display = our table column index (our selection col is 0,
        # Django's action_checkbox is its index 0 — they line up).
        self._ordering_cols = dict(changelist.get_ordering_field_columns())
        self._sortable_positions = set()
        for i, col in enumerate(columns):
            try:
                if changelist.get_ordering_field(col):
                    self._sortable_positions.add(i + 1)
            except Exception:  # noqa: BLE001
                pass

        # Leading selection-indicator column (fixed width).
        table.add_column(" ", key=SELECTION_COLUMN_KEY, width=SELECTION_WIDTH)
        for i, spec in enumerate(self._specs):
            arrow = {"asc": " ▲", "desc": " ▼"}.get(self._ordering_cols.get(i + 1), "")
            label = f"{spec.label}{arrow}"
            width = spec.width + (2 if arrow else 0)
            table.add_column(label, key=spec.key, width=width)

        for obj, cells in zip(objs, full_rows, strict=True):
            pk = str(obj.pk)
            marker = "✓" if pk in self.selected_pks else " "
            row_values = [marker]
            for spec in self._specs:
                row_values.append(truncate_cell(cells[spec.key], spec.width))
            table.add_row(*row_values, key=pk)

    def _refresh_filters(self, changelist) -> None:  # type: ignore[no-untyped-def]
        sidebar = self.query_one("#filter-sidebar", FilterSidebar)
        groups = extract_filter_groups(changelist, self.request)
        sidebar.update_filters(groups)

    def _update_preview(self, pk: str | None) -> None:
        preview = self.query_one("#cell-preview", Static)
        cells = self._full_cells.get(pk) if pk is not None else None
        if not cells:
            preview.update("")
            return
        preview.update(" · ".join(f"{label}: {value}" for label, value in cells))

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
        page = int(self.query_params.get("p", 1))
        if page > 1:
            self.query_params["p"] = page - 1
            self._reset_request_and_rebuild()

    def action_page_next(self) -> None:
        try:
            changelist = _build_changelist(
                self.overlay.model_admin, self.request, query=self.query_params
            )
        except Exception as exc:  # noqa: BLE001
            self._notify_error("Could not page", exc)
            return
        page = getattr(changelist, "page_num", 1)
        if page < changelist.paginator.num_pages:
            self.query_params["p"] = page + 1
            self._reset_request_and_rebuild()

    def action_cycle_sort(self) -> None:
        """Keyboard sort. The row cursor has no column, so `s` cycles the sort
        across the *sortable* columns and direction:
        unsorted → col ▲ → col ▼ → next sortable col → … → unsorted.
        (Click a column header to sort it directly — the Django way.)"""
        positions = sorted(self._sortable_positions)
        if not positions:
            return
        col, descending = self._current_sort()
        if col is None or col not in positions:
            self.query_params["o"] = str(positions[0])
        elif not descending:
            self.query_params["o"] = f"-{col}"
        else:
            later = [p for p in positions if p > col]
            if later:
                self.query_params["o"] = str(later[0])
            else:
                self.query_params.pop("o", None)
        self._reset_request_and_rebuild()
        self._focus_table()

    def _current_sort(self) -> tuple[int | None, bool]:
        """Parse the active `o` param → (1-based column position, descending)."""
        order = str(self.query_params.get("o", "") or "")
        token = order.split(".")[0].strip()
        if not token:
            return None, False
        descending = token.startswith("-")
        num = token[1:] if descending else token
        return (int(num), descending) if num.isdigit() else (None, False)

    def _sort_label(self, changelist) -> str:  # type: ignore[no-untyped-def]
        """A human 'ordered by <column> ▲/▼' label, reflecting the effective
        ordering (including the ModelAdmin's default `ordering`)."""
        ordering = dict(changelist.get_ordering_field_columns())
        if not ordering:
            return ""
        position, order_type = next(iter(ordering.items()))
        columns = list(self.overlay.get_list_columns(self.request))
        label = str(position)
        if 1 <= position <= len(columns):
            label = self._column_label(columns[position - 1])
        return f"ordered by {label} {'▲' if order_type == 'asc' else '▼'}"

    def _sort_by_column_index(self, col_index: int) -> None:
        """Cycle ascending → descending → unsorted for the data column at
        `col_index` (1-based against list_display; index 0 is the selection
        column). Reuses Django's `o` query param (Constitution I)."""
        target = str(col_index)  # Django's `o` is 1-based against list_display.
        current = self.query_params.get("o", "")
        if current == target:
            self.query_params["o"] = f"-{target}"
        elif current == f"-{target}":
            self.query_params.pop("o", None)
        else:
            self.query_params["o"] = target
        self._reset_request_and_rebuild()

    def action_search(self) -> None:
        # If the persistent search bar is present, focus it (the primary search
        # UI). Models without `search_fields` have no bar → fall back to a modal.
        search_bar = self._search_bar()
        if search_bar is not None:
            search_bar.focus()
            return

        def _apply(result: str | None) -> None:
            if result is None:
                return
            stripped = result.strip()
            if stripped:
                self.query_params["q"] = stripped
            else:
                self.query_params.pop("q", None)
            self.query_params.pop("p", None)
            self._reset_request_and_rebuild()

        self.app.push_screen(
            _SearchModal(initial=str(self.query_params.get("q", ""))),
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
        self._toggle_select_pk(str(pk))

    def _toggle_select_pk(self, pk: str) -> None:
        if pk in self.selected_pks:
            self.selected_pks.discard(pk)
        else:
            self.selected_pks.add(pk)
        table = self.query_one("#changelist-table", DataTable)
        self._refresh_selection_indicator(table, pk)
        self._rebuild_header()

    def _rebuild_header(self) -> None:
        try:
            changelist = _build_changelist(
                self.overlay.model_admin, self.request, query=self.query_params
            )
            self._refresh_header(changelist)
        except Exception as exc:  # noqa: BLE001
            self._notify_error("Could not refresh", exc)

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
        """Build the (kind, action_name, label) list shown in the picker."""
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
        """Dispatch an overlay's key-bound row action on the focused row."""
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
        """Refresh after returning from a detail / action / confirm screen."""
        try:
            if self.selected_pks:
                qs = self.overlay.model_admin.get_queryset(self.request)
                existing = set(
                    str(pk)
                    for pk in qs.filter(pk__in=self.selected_pks).values_list(
                        "pk", flat=True
                    )
                )
                self.selected_pks &= existing
        except Exception:  # noqa: BLE001 — stale selection cleanup is best-effort
            self.selected_pks.clear()
        self._reset_request_and_rebuild()
        self.call_after_refresh(self._focus_table)
