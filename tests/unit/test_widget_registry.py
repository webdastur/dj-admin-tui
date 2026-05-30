"""Field-widget registry contract (FR-025, data-model.md § 4).

Pins:
  - MRO walk: a subclass of a registered Field type inherits the parent's widget.
  - Overlay `field_widgets` overrides beat the global registry.
  - Unknown field types fall through to the text-input default.

The registry's contract is "given a BoundField, return a factory callable."
Instantiating the factory's output produces a Textual widget — but Textual
8.x widgets require a running App context, so we don't construct them in
these unit tests. Pilot-driven tests in tests/integration/ exercise widgets
inside a real App.
"""

from __future__ import annotations

from django import forms

from admin_tui.options import TuiAdmin
from admin_tui.widgets.defaults.boolean import boolean_widget
from admin_tui.widgets.defaults.choice import choice_widget
from admin_tui.widgets.defaults.foreign_key import foreign_key_widget
from admin_tui.widgets.defaults.json_field import json_widget
from admin_tui.widgets.defaults.numeric import numeric_widget
from admin_tui.widgets.defaults.text import text_widget
from admin_tui.widgets.registry import FieldWidgetRegistry, field_widgets


def _bound_field(form_field: forms.Field, value=None):
    """Build a BoundField-like minimal stand-in for resolver tests."""

    class _BF:
        field = form_field

        def value(self_inner):
            return value

    return _BF()


def test_text_field_resolves_to_text_widget_factory():
    bf = _bound_field(forms.CharField(), value="hi")
    assert field_widgets.resolve(bf) is text_widget


def test_boolean_field_resolves_to_boolean_widget_factory():
    bf = _bound_field(forms.BooleanField(), value=True)
    assert field_widgets.resolve(bf) is boolean_widget


def test_choice_field_resolves_to_choice_widget_factory():
    bf = _bound_field(forms.ChoiceField(choices=[("a", "A")]), value="a")
    assert field_widgets.resolve(bf) is choice_widget


def test_foreign_key_field_resolves_to_foreign_key_widget_factory():
    bf = _bound_field(
        forms.ModelChoiceField(queryset=None, required=False),
        value=None,
    )
    assert field_widgets.resolve(bf) is foreign_key_widget


def test_json_field_resolves_to_json_widget_factory():
    bf = _bound_field(forms.JSONField(), value={"k": 1})
    assert field_widgets.resolve(bf) is json_widget


def test_numeric_field_resolves_to_numeric_widget_factory():
    bf = _bound_field(forms.IntegerField(), value=1)
    assert field_widgets.resolve(bf) is numeric_widget


def test_mro_walk_picks_up_subclass():
    """A subclass of a registered Field should inherit its widget factory."""

    class CustomChar(forms.CharField):
        pass

    bf = _bound_field(CustomChar(), value="x")
    assert field_widgets.resolve(bf) is text_widget


def test_subclass_of_choice_falls_through_to_choice_widget():
    """Subclasses of ChoiceField inherit the choice widget factory."""

    class CustomChoice(forms.ChoiceField):
        pass

    bf = _bound_field(CustomChoice(choices=[("a", "A")]), value="a")
    assert field_widgets.resolve(bf) is choice_widget


def test_unknown_field_falls_through_to_text_widget_factory():
    """A completely unknown Field class should default to text."""

    class TotallyNovelField(forms.Field):
        pass

    bf = _bound_field(TotallyNovelField(), value="z")
    assert field_widgets.resolve(bf) is text_widget


def test_overlay_override_beats_global_registry():
    """Per-overlay field_widgets must take precedence over global."""
    reg = FieldWidgetRegistry()

    def global_factory(bf):  # noqa: ANN001
        return None

    def overlay_factory(bf):  # noqa: ANN001
        return None

    reg.register(forms.CharField, global_factory)

    class CustomOverlay(TuiAdmin):
        field_widgets = {forms.CharField: overlay_factory}

    overlay = CustomOverlay.__new__(CustomOverlay)
    overlay.field_widgets = CustomOverlay.field_widgets

    bf = _bound_field(forms.CharField(), value="x")
    assert reg.resolve(bf, overlay=overlay) is overlay_factory


def test_resolve_cache_is_warm_after_first_lookup():
    """The MRO walk result is memoised per Field class."""

    class CachedSubclass(forms.CharField):
        pass

    reg = FieldWidgetRegistry()

    def factory(bf):  # noqa: ANN001
        return None

    reg.register(forms.CharField, factory)
    bf = _bound_field(CachedSubclass(), value="x")
    reg.resolve(bf)
    assert CachedSubclass in reg._resolved_cache


def test_register_as_decorator_returns_factory():
    reg = FieldWidgetRegistry()

    @reg.register(forms.IntegerField)
    def my_factory(bf):  # noqa: ANN001
        return None

    bf = _bound_field(forms.IntegerField(), value=1)
    assert reg.resolve(bf) is my_factory
