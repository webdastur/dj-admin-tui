"""Library app TUI overlays — exercises every extension class.

This file is the "sample app covers every extension point" anchor.
CI fails if any of the extension paths declared here break, so do not
delete it without updating the docs.

Extension points exercised:
  1. Custom row action (mark_featured_via_tui).
  2. Custom bulk action (bulk_recolor).
  3. Custom key binding (`f` → mark_featured_via_tui on the focused row).
  4. Per-cell render override (featured books → bold yellow title).
  5. Per-model widget override (ColorFormField → ColorPickerWidget).
  6. Full-screen replacement (Author detail → AuthorStatsScreen).
  7. Lifecycle hooks (before_save sets normalised_title, after_save
     records the call for tests).
  Plus: a global tool screen (`logs`) registered via tui_site.register_screen.
"""

from __future__ import annotations

from typing import Any

from dj_admin_tui import TuiAdmin, field_widgets, register, tui_site
from dj_admin_tui.core.audit import _log_change
from dj_admin_tui.options import BoundCellValue
from sample_project.library.fields import ColorFormField
from sample_project.library.models import Author, Book
from sample_project.library.screens import AuthorStatsScreen, LogEntryScreen
from sample_project.library.tui_widgets import ColorPickerWidget


# 5. Per-model widget override — ColorFormField → ColorPickerWidget.
@field_widgets.register(ColorFormField)
def _color_picker_factory(bound_field):
    return ColorPickerWidget(value=bound_field.value() or "#000000")


@register(Book)
class BookTui(TuiAdmin):
    """TUI overlay for Book — exercises slots 1, 2, 3, 4, 7."""

    # 1, 3 — row action + key binding.
    row_actions = ["mark_featured_via_tui"]
    key_bindings = [("f", "mark_featured_via_tui", "Feature")]

    # 2 — TUI-native bulk action.
    bulk_actions = ["bulk_recolor"]

    # Class-level tracking lists let tests assert that the hooks fired
    # without driving the UI. before_save / after_save append here.
    _before_save_calls: list[tuple[Any, bool]] = []
    _after_save_calls: list[tuple[Any, bool]] = []

    # 4 — per-cell render override.
    def render_cell(self, request, obj, field):
        if field == "title" and getattr(obj, "featured", False):
            return BoundCellValue(display=f"[bold yellow]{obj.title}[/]")
        return super().render_cell(request, obj, field)

    # 1 — TUI-native single-row action.
    def mark_featured_via_tui(self, request, obj):
        if not self.has_change_permission(request, obj):
            return
        obj.featured = True
        obj.save(update_fields=["featured"])
        _log_change(
            self.model_admin,
            request,
            obj,
            [{"changed": {"fields": ["featured"]}}],
        )

    # 2 — TUI-native bulk action.
    def bulk_recolor(self, request, queryset):
        count = queryset.update(color="#FF8800")
        self.model_admin.message_user(
            request,
            f"Recolored {count} book(s) to orange.",
        )

    # 7 — before_save / after_save lifecycle hooks.
    def before_save(self, request, obj, *, created):
        BookTui._before_save_calls.append((obj.pk, created))
        # Populate the normalised_title field — the field isn't on the
        # form (it's a TUI-managed shadow), but before_save runs before
        # save_model, so the value sticks.
        obj.normalised_title = (obj.title or "").strip().lower()

    def after_save(self, request, obj, *, created):
        BookTui._after_save_calls.append((obj.pk, created))


@register(Author)
class AuthorTui(TuiAdmin):
    """6 — Full-screen replacement: Author detail → AuthorStatsScreen."""

    def get_detail_screen(self, request, obj=None):
        return AuthorStatsScreen


# Global tool screen: reachable from the index via `g logs`.
tui_site.register_screen("logs", LogEntryScreen)
