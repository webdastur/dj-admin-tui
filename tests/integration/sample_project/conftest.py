"""Shared fixtures for the v2 integration suites (layout, mouse, save, theming).

The ``showcases`` fixture seeds ``Showcase`` rows with deliberately long text
(for truncation), a filterable status/boolean/FK spread, and related FK/M2M
targets — reused by the layout-stability, mouse-parity, and save-matrix tests.

Uses ``transactional_db`` because Pilot runs the App in a worker thread and the
App's connection must see committed rows (same rationale as test_navigation).
"""

from __future__ import annotations

import datetime as dt

import pytest
from django.utils import timezone

from sample_project.library.models import Author, Showcase, Tag


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
