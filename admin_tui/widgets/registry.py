"""FieldWidgetRegistry — maps model-field classes to Textual widget factories.

Resolution order (per FR-025 / data-model.md § 4):
  1. If the calling overlay has `field_widgets[Field]`, use it.
  2. Walk `type(bound_field.field).__mro__` against the global registry;
     the first match wins. (This is what makes a user subclass of
     `JSONField` inherit the JSONField widget without re-registration.)
  3. Fall through to a text-input default.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from django.db.models import Field
    from django.forms import BoundField
    from textual.widget import Widget

    from admin_tui.options import TuiAdmin


WidgetFactory = Callable[["BoundField"], "Widget"]


class FieldWidgetRegistry:
    """Process-wide mapping from `Field` subclasses to widget factories.

    The default singleton is `admin_tui.field_widgets`. Custom registries
    are not part of the public API at v1.0 (Constitution V).
    """

    def __init__(self) -> None:
        self._table: dict[type["Field"], WidgetFactory] = {}
        self._resolved_cache: dict[type["Field"], WidgetFactory] = {}

    # -- registration ---------------------------------------------------

    def register(
        self,
        field_cls: "type[Field]",
        factory: WidgetFactory | None = None,
    ) -> Any:
        """Register a factory. Usable as a function or decorator.

            field_widgets.register(MyField, my_factory)

            @field_widgets.register(MyField)
            def my_factory(bound_field):
                return MyWidget(...)
        """
        if factory is None:
            # Decorator form: returns a decorator that captures the factory.
            def _decorator(f: WidgetFactory) -> WidgetFactory:
                self._table[field_cls] = f
                self._resolved_cache.clear()
                return f

            return _decorator

        self._table[field_cls] = factory
        self._resolved_cache.clear()
        return factory

    def is_registered(self, field_cls: "type[Field]") -> bool:
        return field_cls in self._table

    # -- resolution -----------------------------------------------------

    def resolve(
        self,
        bound_field: "BoundField",
        overlay: "TuiAdmin | None" = None,
    ) -> WidgetFactory:
        """Pick the best factory for `bound_field`.

        Per-overlay overrides beat the global registry; MRO walk handles
        subclasses; falls back to a text-input default.
        """
        field_cls = type(bound_field.field)

        # 1. Overlay-specific override (exact match — overlays use forms.Field
        #    subclasses, not models.Field).
        if overlay is not None and overlay.field_widgets:
            override = overlay.field_widgets.get(field_cls)
            if override is not None:
                return override

        # 2. Global registry + MRO walk, with memoisation.
        cached = self._resolved_cache.get(field_cls)
        if cached is not None:
            return cached

        for cls in field_cls.__mro__:
            factory = self._table.get(cls)
            if factory is not None:
                self._resolved_cache[field_cls] = factory
                return factory

        # 3. Fallback to text input.
        from admin_tui.widgets.defaults.text import text_widget

        self._resolved_cache[field_cls] = text_widget
        return text_widget


#: The default process-wide field-widget registry. Public API (Constitution V).
field_widgets = FieldWidgetRegistry()
