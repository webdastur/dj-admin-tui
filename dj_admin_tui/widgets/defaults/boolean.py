"""Default widget for boolean fields → Textual Switch."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.widgets import Switch

if TYPE_CHECKING:
    from django.forms import BoundField


def boolean_widget(bound_field: BoundField) -> Switch:
    value = bound_field.value()
    return Switch(value=bool(value))
