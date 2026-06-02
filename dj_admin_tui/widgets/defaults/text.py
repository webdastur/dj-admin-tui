"""Default widget for text-like fields (Char/Email/URL/Slug + Text).

Handles `forms.CharField` and its friends (`EmailField`, `URLField`,
`SlugField`). The rendering follows the *widget* Django chose for the bound
field rather than the field class, because both a model `CharField` and a
model `TextField` map to a form `CharField` — they differ only in their
widget (`TextInput` vs `Textarea`). So a `TextField` (or any field the admin
gives a `Textarea`, e.g. via `formfield_overrides`) renders as a multi-line
Textual `TextArea`; everything else stays a single-line `Input`. This mirrors
the web admin, which renders the same fields as `<textarea>` vs `<input>`
(defer to Django).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django import forms
from textual.widgets import Input, TextArea

if TYPE_CHECKING:
    from django.forms import BoundField
    from textual.widget import Widget


def text_widget(bound_field: BoundField) -> Widget:
    value = bound_field.value()
    text = "" if value is None else str(value)
    if isinstance(bound_field.field.widget, forms.Textarea):
        # Multi-line field (model TextField, or any Textarea-widget field).
        return TextArea(text=text)
    return Input(value=text)
