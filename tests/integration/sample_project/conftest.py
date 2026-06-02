"""Shared fixtures for the v2 integration suites (layout, mouse, save, theming).

The ``showcases`` fixture seeds ``Showcase`` rows with deliberately long text
(for truncation), a filterable status/boolean/FK spread, and related FK/M2M
targets — reused by the layout-stability, mouse-parity, and save-matrix tests.

Uses ``transactional_db`` because Pilot runs the App in a worker thread and the
App's connection must see committed rows (same rationale as test_navigation).
"""

from __future__ import annotations

import datetime as dt
import importlib

import pytest
from django.utils import timezone

from dj_admin_tui.sites import tui_site
from sample_project.library.models import Author, Book, Showcase, Tag


@pytest.fixture
def with_overlays():
    """Reload library.tui so BookTui + AuthorTui + LogEntryScreen register."""
    tui_site._registry.clear()
    tui_site._synth_cache.clear()
    tui_site._screens.clear()
    import sample_project.library.tui as tui_module

    importlib.reload(tui_module)
    yield
    tui_site._registry.clear()
    tui_site._synth_cache.clear()
    tui_site._screens.clear()


@pytest.fixture
def seeded_books(transactional_db):
    """A handful of books spanning 'Tolkien' (2) and 'Lewis' (1).

    Uses ``transactional_db`` (not ``db``) because Pilot runs the App in a
    worker thread, and the App's connection only sees committed rows.
    """
    tolkien = Author.objects.create(name="J.R.R. Tolkien")
    lewis = Author.objects.create(name="C.S. Lewis")
    pratchett = Author.objects.create(name="Terry Pratchett")
    Book.objects.create(
        title="The Hobbit",
        author=tolkien,
        published=dt.date(1937, 9, 21),
        featured=False,
        color="#000000",
    )
    Book.objects.create(
        title="The Lord of the Rings",
        author=tolkien,
        published=dt.date(1954, 7, 29),
        featured=False,
        color="#000000",
    )
    Book.objects.create(
        title="The Lion, the Witch and the Wardrobe",
        author=lewis,
        published=dt.date(1950, 10, 16),
        featured=False,
        color="#000000",
    )
    Book.objects.create(
        title="Mort",
        author=pratchett,
        published=dt.date(1987, 11, 1),
        featured=False,
        color="#000000",
    )
    # Materialise so Pilot's async-context queries don't share a lazy cursor.
    return list(Book.objects.all())


@pytest.fixture
def showcase_targets(transactional_db):
    """FK + M2M targets the showcases relate to."""
    author = Author.objects.create(name="Ada Lovelace")
    t1 = Tag.objects.create(name="alpha")
    t2 = Tag.objects.create(name="beta")
    t3 = Tag.objects.create(name="gamma")
    return {"author": author, "tags": [t1, t2, t3]}


@pytest.fixture
def showcases(showcase_targets):
    """A handful of Showcase rows; the first has a very long description."""
    author = showcase_targets["author"]
    long_desc = (
        "This is an intentionally very long description that overflows any "
        "reasonable terminal column width so the truncation and footer-preview "
        "behaviour can be exercised end to end without reflowing the table."
    )
    rows = []
    rows.append(
        Showcase.objects.create(
            title="Widget One",
            description=long_desc,
            is_active=True,
            status="published",
            author=author,
            release_date=dt.date(2024, 1, 15),
            created_at=timezone.make_aware(dt.datetime(2024, 1, 15, 9, 30)),
            quantity=12,
            price="9.99",
        )
    )
    rows.append(
        Showcase.objects.create(
            title="Widget Two",
            description="Short.",
            is_active=False,
            status="draft",
            author=author,
            quantity=3,
            price="1.50",
        )
    )
    rows.append(
        Showcase.objects.create(
            title="Widget Three",
            description="Medium length description here.",
            is_active=True,
            status="review",
            quantity=0,
            price="0.00",
        )
    )
    # Attach M2M to the first row so the save matrix has a baseline.
    rows[0].tags.set(showcase_targets["tags"][:2])
    return list(Showcase.objects.all())
