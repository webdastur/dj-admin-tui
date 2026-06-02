"""Default widget for Date / Time / DateTime fields → Textual Input."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.widgets import Input

if TYPE_CHECKING:
    from django.forms import BoundField


def datetime_widget(bound_field: BoundField) -> Input:
    value = bound_field.value()
    # Form fields surface the value as a string already (`as_widget()`-style).
    return Input(value="" if value is None else str(value))
