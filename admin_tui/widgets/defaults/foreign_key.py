"""Default widget for ModelChoiceField → simple Select scoped by ModelAdmin.

For v1 this is a plain Select over the queryset. T070-style autocomplete
(narrowing as the user types) is a follow-up if a real need surfaces.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from textual.widgets import Select

if TYPE_CHECKING:
    from django.forms import BoundField


def foreign_key_widget(bound_field: "BoundField") -> Select[Any]:
    field = bound_field.field
    queryset = getattr(field, "queryset", None)
    options: list[tuple[str, Any]] = []
    if queryset is not None:
        for obj in queryset[:1000]:  # bound to avoid loading huge FK targets
            options.append((str(obj), obj.pk))
    current = bound_field.value()
    # Textual's Select rejects value=None and any value absent from the options.
    # Only pass `value` when the current value is a real option (e.g. a nullable
    # FK on an add form has no current value → leave it unselected).
    option_values = {v for _, v in options}
    kwargs: dict[str, Any] = {"options": options, "allow_blank": True}
    if current in option_values:
        kwargs["value"] = current
    return Select(**kwargs)
