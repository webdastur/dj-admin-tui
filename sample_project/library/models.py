"""Sample library models — exercise the full TUI surface end-to-end.

Coverage targets:
  - FK and M2M relations (Author, Tag).
  - JSONField (metadata).
  - DateField and BooleanField (published, featured, archived).
  - TextField (summary, bio).
  - Custom ColorField (added by US4 / T069).

The Book.archived flag exists so `BookAdmin` can declare a bulk action
that mutates it (T041 — exercises FR-017 bulk-action surface).
"""

from __future__ import annotations

from django.db import models


class Tag(models.Model):
    name = models.CharField(max_length=64, unique=True)

    class Meta:
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name


class Author(models.Model):
    name = models.CharField(max_length=128)
    bio = models.TextField(blank=True, default="")
    born = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name


class Book(models.Model):
    title = models.CharField(max_length=256)
    author = models.ForeignKey(
        Author,
        on_delete=models.CASCADE,
        related_name="books",
    )
    tags = models.ManyToManyField(Tag, related_name="books", blank=True)
    summary = models.TextField(blank=True, default="")
    published = models.DateField(null=True, blank=True)
    featured = models.BooleanField(default=False)
    archived = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ("title",)

    def __str__(self) -> str:
        return self.title
