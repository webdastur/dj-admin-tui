"""ModelAdmin registrations for the library sample app.

Standard admin — no TUI-specific config. The TUI's default-overlay
synthesis (Constitution III) makes these models work in the terminal
without any additional declarations.

The `library/tui.py` overlay (added in US4 / T071) layers TUI-only
behaviour on top of this admin.
"""

from __future__ import annotations

from django import forms
from django.contrib import admin, messages

from sample_project.library.models import Author, Book, BookChapter, Tag


class BookChapterInline(admin.TabularInline):
    """Stock TabularInline — exercises the inline rendering path (R15)."""

    model = BookChapter
    extra = 0
    fields = ("ordering", "title")


class BookForm(forms.ModelForm):
    """Admin form for Book that demonstrates a custom validator.

    Used by tests/integration/sample_project/test_crud.py to exercise
    FR-013 (a `clean_*` rejection is surfaced + blocks save) without
    leaking test-only logic into production code.
    """

    class Meta:
        model = Book
        fields = "__all__"

    def clean_title(self):
        title = self.cleaned_data["title"]
        if title.strip().lower() == "forbidden":
            raise forms.ValidationError(
                "The word 'forbidden' is reserved — pick another title."
            )
        return title


@admin.action(
    description="Mark selected books as featured",
    permissions=["change"],
)
def mark_featured_action(modeladmin, request, queryset):  # type: ignore[no-untyped-def]
    count = queryset.update(featured=True)
    modeladmin.message_user(
        request,
        f"{count} book(s) were updated.",
        level=messages.SUCCESS,
    )


@admin.action(
    description="Archive selected books",
    permissions=["change"],
)
def archive_selected_action(modeladmin, request, queryset):  # type: ignore[no-untyped-def]
    count = queryset.update(archived=True)
    modeladmin.message_user(
        request,
        f"Archived {count} book(s).",
        level=messages.SUCCESS,
    )


@admin.action(
    description="Failing action (testing FR-019 error path)",
    permissions=["change"],
)
def failing_action(modeladmin, request, queryset):  # type: ignore[no-untyped-def]
    """Exercises FR-019: emit a message, then raise.

    `_run_action` must capture the message, surface the exception, and
    NOT fire `after_action`'s success branch.
    """
    modeladmin.message_user(
        request,
        "starting…",
        level=messages.INFO,
    )
    raise RuntimeError("boom")


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    form = BookForm
    list_display = ("title", "author", "published", "featured", "archived")
    list_filter = ("featured", "archived", "published")
    search_fields = ("title", "author__name")
    actions = [
        mark_featured_action,
        archive_selected_action,
        failing_action,
    ]
    inlines = [BookChapterInline]
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
