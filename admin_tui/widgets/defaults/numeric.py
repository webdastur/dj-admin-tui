"""Default widget for Integer / Float / Decimal fields → Textual Input."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.widgets import Input

if TYPE_CHECKING:
    from django.forms import BoundField


def numeric_widget(bound_field: "BoundField") -> Input:
    value = bound_field.value()
    return Input(value="" if value is None else str(value))
