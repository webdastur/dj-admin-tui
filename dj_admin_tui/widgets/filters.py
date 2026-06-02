"""FilterSidebar — renders Django's own ``list_filter`` specs.

The TUI never computes a filter predicate. This widget reads
the filter specs off the ``ChangeList`` the changelist already built
(``changelist.get_filters(request)``) and renders each spec's title and
``spec.choices(changelist)`` entries. Choosing an entry posts a
``FilterSidebar.FilterChosen`` message carrying Django's own ``query_string``;
the changelist screen applies it verbatim.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from textual.containers import VerticalScroll
from textual.message import Message
from textual.widgets import OptionList, Static
from textual.widgets.option_list import Option

if TYPE_CHECKING:
    from django.http import HttpRequest


def extract_filter_groups(
    changelist: Any, request: HttpRequest
) -> list[tuple[str, list[dict[str, Any]]]]:
    """Return ``[(title, [choice_dict, ...]), ...]`` from a built ChangeList.

    Each ``choice_dict`` has Django's ``display`` / ``selected`` /
    ``query_string`` keys. Returns ``[]`` when the model declares no
    ``list_filter`` (or the specs produce no output).
    """
    try:
        filter_specs = changelist.get_filters(request)[0]
    except Exception:
        return []
    groups: list[tuple[str, list[dict[str, Any]]]] = []
    for spec in filter_specs or []:
        try:
            choices = list(spec.choices(changelist))
        except Exception:
            continue
        groups.append((str(spec.title), choices))
    return groups


class FilterSidebar(VerticalScroll):
    """A right-docked panel mirroring the admin's filter sidebar."""

    class FilterChosen(Message):
        """Posted when the operator picks a filter choice."""

        def __init__(self, query_string: str) -> None:
            super().__init__()
            self.query_string = query_string

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        # Maps an OptionList option id -> Django query_string.
        self._query_by_id: dict[str, str] = {}

    def compose(self):  # type: ignore[no-untyped-def]
        yield Static("[b]Filter[/]", id="filter-title")
        yield OptionList(id="filter-options")

    def update_filters(self, groups: list[tuple[str, list[dict[str, Any]]]]) -> None:
        """Rebuild the sidebar from extracted filter groups.

        Hides itself when there are no groups so models without ``list_filter``
        show no empty sidebar.
        """
        self.display = bool(groups)
        if not self.is_mounted:
            return
        option_list = self.query_one("#filter-options", OptionList)
        option_list.clear_options()
        self._query_by_id.clear()
        counter = 0
        for title, choices in groups:
            option_list.add_option(Option(f"[b]{title}[/]", disabled=True))
            for choice in choices:
                counter += 1
                opt_id = f"f{counter}"
                self._query_by_id[opt_id] = choice.get("query_string", "?")
                marker = "●" if choice.get("selected") else "○"
                display = choice.get("display", "")
                option_list.add_option(Option(f"  {marker} {display}", id=opt_id))

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        opt_id = event.option_id
        if opt_id is None:
            return
        query_string = self._query_by_id.get(opt_id)
        if query_string is not None:
            self.post_message(self.FilterChosen(query_string))
