"""ModelAdmin registrations for the library sample app.

Standard admin — no TUI-specific config. The TUI's default-overlay
synthesis (Constitution III) makes these models work in the terminal
without any additional declarations.

The `library/tui.py` overlay (added in US4 / T071) layers TUI-only
behaviour on top of this admin.
"""

from __future__ import annotations

from django.contrib import admin, messages

from sample_project.library.models import Author, Book, Tag


@admin.action(description="Mark selected books as featured")
def mark_featured_action(modeladmin, request, queryset):  # type: ignore[no-untyped-def]
    count = queryset.update(featured=True)
    modeladmin.message_user(
        request,
        f"{count} book(s) were updated.",
        level=messages.SUCCESS,
    )


@admin.action(description="Archive selected books")
def archive_selected_action(modeladmin, request, queryset):  # type: ignore[no-untyped-def]
    count = queryset.update(archived=True)
    modeladmin.message_user(
        request,
        f"Archived {count} book(s).",
        level=messages.SUCCESS,
    )


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "published", "featured", "archived")
    list_filter = ("featured", "archived", "published")
    search_fields = ("title", "author__name")
    actions = ("mark_featured_action", "archive_selected_action")
    autocomplete_fields = ("author",)
    list_per_page = 50


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ("name", "born")
    search_fields = ("name",)
    list_per_page = 50


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
