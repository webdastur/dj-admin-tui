"""TuiAdmin — per-model overlay base class, plus the `@register` decorator.

Public API. The full contract is in docs/api.md and docs/extending.md.

Defaults travel the extension path: a model with no
explicit overlay is wrapped in a `TuiAdmin` instance synthesised from its
`ModelAdmin` — same class, same code path as user-written overlays.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from admin_tui.sites import AlreadyRegistered, tui_site

if TYPE_CHECKING:
    from django.contrib.admin import ModelAdmin
    from django.db.models import Field, Model, QuerySet
    from django.http import HttpRequest
    from textual.screen import Screen
    from textual.widget import Widget

    from admin_tui.sites import TuiSite


# -- helpers exposed via overlay (not in the top-level public surface) --


@dataclass(frozen=True)
class BoundCellValue:
    """Return value of `TuiAdmin.render_cell(...)`."""

    display: str
    sort_key: Any = None
    style: str | None = None


# -- TuiAdmin -----------------------------------------------------------


class TuiAdmin:
    """Per-model overlay. Subclass to customise TUI behaviour for a model.

    Every model rendered by the TUI is backed by exactly one TuiAdmin —
    either a synthesised default (zero-config) or a user-written subclass.
    The instance retains a pointer to the underlying ModelAdmin so every
    default delegates to it (Constitution I — no parallel logic).
    """

    # -- declarative slots (each defaults to None / [] / {}) ------------

    list_columns: Sequence[str] | None = None
    detail_fieldsets: Any | None = None
    row_actions: list[str] = []
    bulk_actions: list[str] = []
    key_bindings: list[tuple[str, str, str]] = []
    field_widgets: dict[Any, Callable[..., "Widget"]] = {}

    # -- construction / synthesis --------------------------------------

    def __init__(self, model_admin: "ModelAdmin") -> None:
        self.model_admin = model_admin

    @classmethod
    def _synthesize(cls, model_admin: "ModelAdmin") -> "TuiAdmin":
        """Build a default overlay around an existing ModelAdmin.

        Used by `TuiSite.get_or_synthesize(...)` when no explicit overlay
        is registered. Subclasses inherit this so the synth path always
        constructs the right class.
        """
        return cls(model_admin)

    # -- list / detail surface -----------------------------------------

    def get_list_columns(self, request: "HttpRequest") -> Sequence[str]:
        if self.list_columns is not None:
            return self.list_columns
        return self.model_admin.get_list_display(request)

    def get_queryset(self, request: "HttpRequest") -> "QuerySet":
        return self.model_admin.get_queryset(request)

    def render_cell(
        self,
        request: "HttpRequest",
        obj: Any,
        field: str,
    ) -> BoundCellValue:
        """Render one changelist cell.

        Default: read the attribute (or call it, if it's a method) and
        coerce to string. Subclasses override per-column.
        """
        value = getattr(obj, field, "")
        if callable(value):
            value = value()
        return BoundCellValue(display=str(value))

    # -- actions --------------------------------------------------------

    def get_row_actions(
        self,
        request: "HttpRequest",
        obj: Any,
    ) -> list[str]:
        if not self.row_actions:
            return []
        return [a for a in self.row_actions if self.has_change_permission(request, obj)]

    def get_bulk_actions(self, request: "HttpRequest") -> list[str]:
        if not self.bulk_actions:
            return []
        return [a for a in self.bulk_actions if self.has_change_permission(request)]

    # -- screen routing (full-screen replacement extension point) ------

    def get_changelist_screen(
        self,
        request: "HttpRequest",
    ) -> "type[Screen]":
        """Return the Screen class to render this model's changelist.

        Default returns `admin_tui.screens.changelist.ChangelistScreen`.
        Override to substitute a custom Textual `Screen` subclass.
        """
        from admin_tui.screens.changelist import ChangelistScreen

        return ChangelistScreen

    def get_detail_screen(
        self,
        request: "HttpRequest",
        obj: Any | None = None,
    ) -> "type[Screen]":
        """Return the Screen class to render this model's detail view."""
        from admin_tui.screens.change import ChangeScreen

        return ChangeScreen

    # -- lifecycle hooks ------------------------------------------------

    def before_save(
        self,
        request: "HttpRequest",
        obj: Any,
        *,
        created: bool,
    ) -> None: ...

    def after_save(
        self,
        request: "HttpRequest",
        obj: Any,
        *,
        created: bool,
    ) -> None: ...

    def before_action(
        self,
        request: "HttpRequest",
        action: str,
        queryset: "QuerySet",
    ) -> None: ...

    def after_action(
        self,
        request: "HttpRequest",
        action: str,
        queryset: "QuerySet",
        *,
        result: Any = None,
    ) -> None: ...

    # -- permission delegation -----------------------------------------

    def has_view_permission(
        self,
        request: "HttpRequest",
        obj: Any | None = None,
    ) -> bool:
        return self.model_admin.has_view_permission(request, obj)

    def has_add_permission(self, request: "HttpRequest") -> bool:
        return self.model_admin.has_add_permission(request)

    def has_change_permission(
        self,
        request: "HttpRequest",
        obj: Any | None = None,
    ) -> bool:
        return self.model_admin.has_change_permission(request, obj)

    def has_delete_permission(
        self,
        request: "HttpRequest",
        obj: Any | None = None,
    ) -> bool:
        return self.model_admin.has_delete_permission(request, obj)


# -- @register decorator -------------------------------------------------


def register(
    *models: "type[Model]",
    site: "TuiSite" = tui_site,
) -> Callable[[type[TuiAdmin]], type[TuiAdmin]]:
    """Class decorator: register a TuiAdmin overlay for one or more models.

    Mirrors `django.contrib.admin.register`. Usage:

        @register(Book)
        class BookTui(TuiAdmin):
            row_actions = ["mark_featured"]

        @register(Book, Author)
        class SharedTui(TuiAdmin):
            ...

    Raises `AlreadyRegistered` on duplicates and `ImproperlyConfigured` if
    the model isn't registered with django.contrib.admin.
    """
    if not models:
        raise ValueError("register() requires at least one model.")

    def decorator(overlay_cls: type[TuiAdmin]) -> type[TuiAdmin]:
        if not issubclass(overlay_cls, TuiAdmin):
            raise TypeError(
                f"{overlay_cls.__name__} must be a subclass of TuiAdmin."
            )
        for model in models:
            site.register(model, overlay_cls)
        return overlay_cls

    return decorator


__all__ = ["TuiAdmin", "BoundCellValue", "register", "AlreadyRegistered"]
