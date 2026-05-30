"""Default widget for choice / typed-choice fields → Textual Select."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from textual.widgets import Select

if TYPE_CHECKING:
    from django.forms import BoundField


def choice_widget(bound_field: "BoundField") -> Select[Any]:
    raw_choices = getattr(bound_field.field, "choices", None) or []
    options: list[tuple[str, Any]] = []
    for value, label in raw_choices:
        # Django uses an empty value with a label like "---------" for the
        # "no selection" entry — keep it.
        options.append((str(label), value))
    current = bound_field.value()
    return Select(options=options, value=current, allow_blank=True)
