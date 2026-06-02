"""Default widget for ModelMultipleChoiceField (M2M) → Textual SelectionList.

v1 mapped ``ModelMultipleChoiceField`` to the single-value foreign-key Select,
so many-to-many fields could not hold multiple values and failed
``ModelMultipleChoiceField`` validation ("Enter a list of values"). A
``SelectionList`` returns a list of selected pks, which the save path now
gathers correctly.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from textual.widgets import SelectionList
from textual.widgets.selection_list import Selection

if TYPE_CHECKING:
    from django.forms import BoundField

#: Cap on options materialized — mirrors the foreign-key widget (avoids loading
#: an unbounded M2M target table).
_MAX_OPTIONS = 1000


def many_to_many_widget(bound_field: BoundField) -> SelectionList[str]:
    field = bound_field.field
    current = bound_field.value() or []
    current_set = {str(v) for v in current}

    selections: list[Selection[str]] = []
    for i, (val, label) in enumerate(field.choices):
        if i >= _MAX_OPTIONS:
            break
        # ModelChoiceIteratorValue wraps the pk; `.value` is the raw pk.
        pk = getattr(val, "value", val)
        if pk in ("", None):
            continue  # M2M has no blank choice, but be defensive
        selections.append(Selection(str(label), str(pk), str(pk) in current_set))
    return SelectionList[str](*selections)


def read_many_to_many(widget: Any) -> list[str]:
    """Pull the selected pks (as strings) out of a SelectionList."""
    return [str(v) for v in widget.selected]
