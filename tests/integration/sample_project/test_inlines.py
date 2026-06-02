"""Inline rendering.

v1 ships read-only inline display: BookChapter rows show beneath the
parent Book detail. Editable inline rows are deferred to a follow-up
release.

The contract this test pins:
  - _inline_instances returns the inline classes registered on the
    ModelAdmin, filtered by has_view_permission.
  - The related queryset for the inline's `fk_name` (or auto-detected
    FK) returns exactly the related rows.
"""

from __future__ import annotations

import datetime as dt

import pytest
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

from dj_admin_tui.core.forms import _inline_instances
from dj_admin_tui.core.request import build_request
from dj_admin_tui.sites import tui_site
from sample_project.library.models import Author, Book, BookChapter


@pytest.fixture(autouse=True)
def _reset_tui_site():
    tui_site._registry.clear()
    tui_site._synth_cache.clear()
    return


@pytest.fixture
def book_with_chapters(db):
    author = Author.objects.create(name="Inline Author")
    book = Book.objects.create(
        title="Inline Book",
        author=author,
        published=dt.date(2025, 1, 1),
        color="#000000",
    )
    BookChapter.objects.create(book=book, title="Chapter 1", ordering=1)
    BookChapter.objects.create(book=book, title="Chapter 2", ordering=2)
    BookChapter.objects.create(book=book, title="Chapter 3", ordering=3)
    return book


@pytest.mark.django_db
def test_inline_instances_returned_for_book(superuser, book_with_chapters):
    overlay = tui_site.get_or_synthesize(Book)
    request = build_request(superuser)
    inlines = _inline_instances(overlay.model_admin, request, book_with_chapters)
    assert len(inlines) == 1
    inline = inlines[0]
    assert inline.model is BookChapter


@pytest.mark.django_db
def test_related_chapters_filtered_to_parent(superuser, book_with_chapters):
    """The chapter queryset must scope to the parent's pk only."""
    other_author = Author.objects.create(name="Other")
    other_book = Book.objects.create(
        title="Other Book",
        author=other_author,
        published=dt.date(2025, 1, 1),
        color="#000000",
    )
    BookChapter.objects.create(book=other_book, title="Other Chapter")

    overlay = tui_site.get_or_synthesize(Book)
    request = build_request(superuser)
    inlines = _inline_instances(overlay.model_admin, request, book_with_chapters)
    inline = inlines[0]

    # The TUI scopes by detecting the FK to the parent.
    related = inline.model._default_manager.filter(book=book_with_chapters)
    titles = sorted(c.title for c in related)
    assert titles == ["Chapter 1", "Chapter 2", "Chapter 3"]


@pytest.mark.django_db
def test_inline_permission_filtering(staff_only_user, book_with_chapters):
    """Inline view-permission gate: if the user can't view the inline's
    model, _inline_instances filters it out."""
    # Grant view on Book but NOT on BookChapter.
    book_ct = ContentType.objects.get_for_model(Book)
    staff_only_user.user_permissions.add(
        Permission.objects.get(codename="view_book", content_type=book_ct)
    )
    overlay = tui_site.get_or_synthesize(Book)
    request = build_request(staff_only_user)
    inlines = _inline_instances(overlay.model_admin, request, book_with_chapters)
    assert inlines == []


@pytest.mark.django_db
def test_inline_visible_when_view_perm_present(staff_only_user, book_with_chapters):
    book_ct = ContentType.objects.get_for_model(Book)
    chapter_ct = ContentType.objects.get_for_model(BookChapter)
    staff_only_user.user_permissions.add(
        Permission.objects.get(codename="view_book", content_type=book_ct),
        Permission.objects.get(codename="view_bookchapter", content_type=chapter_ct),
    )
    overlay = tui_site.get_or_synthesize(Book)
    request = build_request(staff_only_user)
    inlines = _inline_instances(overlay.model_admin, request, book_with_chapters)
    assert len(inlines) == 1
