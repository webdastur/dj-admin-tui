"""Default widget for text-like fields (Char/Email/URL/Slug).

Handles `forms.CharField`, `forms.EmailField`, `forms.URLField`,
`forms.SlugField`. Renders a Textual `Input` bound to the field's value.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.widgets import Input

if TYPE_CHECKING:
    from django.forms import BoundField


def text_widget(bound_field: "BoundField") -> Input:
    value = bound_field.value()
    return Input(value="" if value is None else str(value))
