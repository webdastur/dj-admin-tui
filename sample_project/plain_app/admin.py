"""Stock admin for plain_app.Note — intentionally has NO tui.py companion."""

from __future__ import annotations

from django.contrib import admin

from sample_project.plain_app.models import Note


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ("title",)
    search_fields = ("title", "body")
