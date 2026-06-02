"""Default widget for JSONField → multi-line Textual TextArea.

We render the JSON-encoded value as-is; the form's `clean()` step parses
and validates it (so we don't reimplement JSON parsing).
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from textual.widgets import TextArea

if TYPE_CHECKING:
    from django.forms import BoundField


def json_widget(bound_field: BoundField) -> TextArea:
    value = bound_field.value()
    if value is None:
        text = ""
    elif isinstance(value, str):
        text = value
    else:
        text = json.dumps(value, indent=2, default=str)
    return TextArea(text=text, language="json")
