"""Sample library models — exercise the full TUI surface end-to-end.

Coverage targets:
  - FK and M2M relations (Author, Tag).
  - JSONField (metadata).
  - DateField and BooleanField (published, featured, archived).
  - TextField (summary, bio).
  - Custom ColorField.

The Book.archived flag exists so `BookAdmin` can declare a bulk action
that mutates it (exercises the bulk-action surface).
"""

from __future__ import annotations

from django.db import models

from sample_project.library.fields import ColorField


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
    color = ColorField()
    # Populated by BookTui.before_save (lifecycle-hook demonstration).
    # `editable=False` keeps it out of every form (admin + TUI), so the
    # only path that writes it is the overlay's lifecycle hook.
    normalised_title = models.CharField(max_length=256, blank=True, default="", editable=False)

    class Meta:
        ordering = ("title",)

    def __str__(self) -> str:
        return self.title


class Showcase(models.Model):
    """Covers the full default-widget set for the v2 save matrix and the
    wide-column truncation / filter tests.

    Intentionally additive — separate table from `Book` so v1 fixtures and
    tests are untouched. `description` holds long values for truncation;
    `list_filter` spans a boolean, a choices field, and an FK.
    """

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("review", "In review"),
        ("published", "Published"),
        ("archived", "Archived"),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    author = models.ForeignKey(
        Author,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="showcases",
    )
    tags = models.ManyToManyField(Tag, related_name="showcases", blank=True)
    release_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    quantity = models.IntegerField(default=0)
    price = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    class Meta:
        ordering = ("title",)

    def __str__(self) -> str:
        return self.title


class BookChapter(models.Model):
    """Inline relation to Book — fixture for the inlines test."""

    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name="chapters",
    )
    title = models.CharField(max_length=128)
    ordering = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("ordering", "title")

    def __str__(self) -> str:
        return f"{self.book.title} — {self.title}"
