"""Register all default widget factories on import.

Imported by `dj_admin_tui.widgets` for its side effect — registering the
defaults on the global `field_widgets` registry. Adding a new built-in
widget means: write the module, then add a `field_widgets.register(...)`
line here.
"""

from __future__ import annotations

from django import forms

from dj_admin_tui.widgets.defaults.boolean import boolean_widget
from dj_admin_tui.widgets.defaults.choice import choice_widget
from dj_admin_tui.widgets.defaults.datetime import datetime_widget
from dj_admin_tui.widgets.defaults.foreign_key import foreign_key_widget
from dj_admin_tui.widgets.defaults.json_field import json_widget
from dj_admin_tui.widgets.defaults.many_to_many import many_to_many_widget
from dj_admin_tui.widgets.defaults.numeric import numeric_widget
from dj_admin_tui.widgets.defaults.text import text_widget
from dj_admin_tui.widgets.registry import field_widgets

# Text-like.
field_widgets.register(forms.CharField, text_widget)
field_widgets.register(forms.EmailField, text_widget)
field_widgets.register(forms.URLField, text_widget)
field_widgets.register(forms.SlugField, text_widget)

# Booleans.
field_widgets.register(forms.BooleanField, boolean_widget)
field_widgets.register(forms.NullBooleanField, boolean_widget)

# Choices.
field_widgets.register(forms.ChoiceField, choice_widget)
field_widgets.register(forms.TypedChoiceField, choice_widget)

# ForeignKey / ModelChoiceField.
field_widgets.register(forms.ModelChoiceField, foreign_key_widget)
# ManyToMany → a real multi-select (NOT the single-value FK Select).
field_widgets.register(forms.ModelMultipleChoiceField, many_to_many_widget)

# Date / Time / DateTime.
field_widgets.register(forms.DateField, datetime_widget)
field_widgets.register(forms.TimeField, datetime_widget)
field_widgets.register(forms.DateTimeField, datetime_widget)

# JSON.
field_widgets.register(forms.JSONField, json_widget)

# Numeric.
field_widgets.register(forms.IntegerField, numeric_widget)
field_widgets.register(forms.FloatField, numeric_widget)
field_widgets.register(forms.DecimalField, numeric_widget)
