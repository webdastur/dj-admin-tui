"""Changelist parity with the web admin.

The contract is "indistinguishable from the web admin's changelist
for the same query parameters." We assert that directly: build a
ChangeList via `_build_changelist(...)` with a `query=` dict and compare
its `.result_list` (and other key attributes) to the same `ChangeList`
the `ModelAdmin` would produce.

Because we route through `model_admin.get_changelist_instance(request)`,
the comparison is essentially identity — but the test
pins it so a future refactor can't silently fork the behavior.
"""

from __future__ import annotations

import datetime as dt

import pytest

from dj_admin_tui.core.changelist import _build_changelist
from dj_admin_tui.core.request import build_request
from sample_project.library.models import Author, Book, Tag


@pytest.fixture
def books(db):
    a_tolkien = Author.objects.create(name="J.R.R. Tolkien")
    a_lewis = Author.objects.create(name="C.S. Lewis")
    a_pratchett = Author.objects.create(name="Terry Pratchett")
    Tag.objects.create(name="fantasy")
    Tag.objects.create(name="classic")

    Book.objects.create(
        title="The Hobbit",
        author=a_tolkien,
        published=dt.date(1937, 9, 21),
        featured=True,
    )
    Book.objects.create(
        title="The Lord of the Rings",
        author=a_tolkien,
        published=dt.date(1954, 7, 29),
        featured=True,
    )
    Book.objects.create(
        title="The Lion, the Witch and the Wardrobe",
        author=a_lewis,
        published=dt.date(1950, 10, 16),
        featured=False,
    )
    Book.objects.create(
        title="Mort",
        author=a_pratchett,
        published=dt.date(1987, 11, 1),
        featured=False,
    )
    Book.objects.create(
        title="Reaper Man",
        author=a_pratchett,
        published=dt.date(1991, 5, 14),
        featured=False,
    )
    return Book.objects.all()


def _book_admin():
    from django.contrib import admin

    return admin.site._registry[Book]


@pytest.mark.django_db
def test_default_changelist_returns_every_row(superuser, books):
    request = build_request(superuser)
    cl = _build_changelist(_book_admin(), request)
    assert cl.result_list.count() == 5


@pytest.mark.django_db
def test_search_narrows_by_search_fields(superuser, books):
    request = build_request(superuser)
    cl = _build_changelist(_book_admin(), request, query={"q": "Tolkien"})
    titles = {b.title for b in cl.result_list}
    assert titles == {"The Hobbit", "The Lord of the Rings"}


@pytest.mark.django_db
def test_search_matches_title_substring(superuser, books):
    request = build_request(superuser)
    cl = _build_changelist(_book_admin(), request, query={"q": "Reaper"})
    titles = {b.title for b in cl.result_list}
    assert titles == {"Reaper Man"}


@pytest.mark.django_db
def test_filter_narrows_by_list_filter(superuser, books):
    request = build_request(superuser)
    cl = _build_changelist(
        _book_admin(),
        request,
        query={"featured__exact": "1"},
    )
    titles = {b.title for b in cl.result_list}
    assert titles == {"The Hobbit", "The Lord of the Rings"}


@pytest.mark.django_db
def test_filter_negation_narrows_to_unfeatured(superuser, books):
    request = build_request(superuser)
    cl = _build_changelist(
        _book_admin(),
        request,
        query={"featured__exact": "0"},
    )
    titles = {b.title for b in cl.result_list}
    assert titles == {
        "The Lion, the Witch and the Wardrobe",
        "Mort",
        "Reaper Man",
    }


@pytest.mark.django_db
def test_pagination_respects_list_per_page(superuser, books, monkeypatch):
    # Force a small page size so we can assert on boundaries.
    monkeypatch.setattr(_book_admin(), "list_per_page", 2)
    request = build_request(superuser)
    cl_page_1 = _build_changelist(_book_admin(), request, query={"p": 1})
    cl_page_2 = _build_changelist(_book_admin(), request, query={"p": 2})
    cl_page_3 = _build_changelist(_book_admin(), request, query={"p": 3})
    assert cl_page_1.paginator.num_pages == 3
    assert len(list(cl_page_1.result_list)) == 2
    assert len(list(cl_page_2.result_list)) == 2
    assert len(list(cl_page_3.result_list)) == 1


@pytest.mark.django_db
def test_result_set_matches_direct_get_changelist_instance(superuser, books):
    """Indistinguishable from what the web admin would produce."""
    request_a = build_request(superuser, query={"q": "Tolkien"})
    request_b = build_request(superuser, query={"q": "Tolkien"})
    via_admin = _book_admin().get_changelist_instance(request_a)
    via_tui = _build_changelist(_book_admin(), request_b, query={"q": "Tolkien"})
    pks_admin = list(via_admin.result_list.values_list("pk", flat=True))
    pks_tui = list(via_tui.result_list.values_list("pk", flat=True))
    assert pks_admin == pks_tui


@pytest.mark.django_db
def test_overlay_get_list_columns_matches_modeladmin(superuser, books):
    """The columns the TUI renders come from `overlay.get_list_columns(...)`,
    which delegates to `ModelAdmin.get_list_display(...)`. Django's
    ChangeList internally prepends `action_checkbox` for action selection
    — that's a web-admin rendering concern; the TUI uses its own selection
    mechanism and reads the un-prepended list_display."""
    from dj_admin_tui.sites import tui_site

    request = build_request(superuser)
    overlay = tui_site.get_or_synthesize(Book)
    columns = tuple(overlay.get_list_columns(request))
    assert columns == ("title", "author", "published", "featured", "archived")
    # And ModelAdmin.get_list_display agrees:
    assert columns == tuple(_book_admin().get_list_display(request))


@pytest.mark.django_db
def test_combined_filter_plus_search(superuser, books):
    """A filter and a search together narrow correctly."""
    request = build_request(superuser)
    cl = _build_changelist(
        _book_admin(),
        request,
        query={"q": "Tolkien", "featured__exact": "1"},
    )
    titles = {b.title for b in cl.result_list}
    # Both Tolkien books are featured, so search ∩ filter = both Tolkien books.
    assert titles == {"The Hobbit", "The Lord of the Rings"}
