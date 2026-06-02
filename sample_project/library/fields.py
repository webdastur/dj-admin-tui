"""Custom field types for the sample library app.

ColorField + ColorFormField exist so the field-widget registry has a
specific form-field class to target. Mapping to plain `forms.CharField`
would also catch every other CharField on the form, which isn't what
the custom-widget demo wants. The custom form-field subclass is the
idiom for "this field has a custom widget."
"""

from __future__ import annotations

from django import forms
from django.core.validators import RegexValidator
from django.db import models

HEX_COLOR_VALIDATOR = RegexValidator(
    regex=r"^#[0-9A-Fa-f]{6}$",
    message="Color must be in #RRGGBB format (e.g. #FF8800).",
)


class ColorFormField(forms.CharField):
    """Form field for hex color strings — distinct class for widget targeting."""

    default_validators = [HEX_COLOR_VALIDATOR]


class ColorField(models.CharField):
    """Stores a 7-char hex color string ('#RRGGBB')."""

    description = "Hex color string (#RRGGBB)"

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_length", 7)
        kwargs.setdefault("default", "#000000")
        super().__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        defaults = {"form_class": ColorFormField}
        defaults.update(kwargs)
        return super().formfield(**defaults)
