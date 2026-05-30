"""SC-002 performance baseline — 100k-row changelist page transitions.

Seeds 100,000 Book rows via bulk_create, then times 10 consecutive
page transitions through `_build_changelist`. The page-transition
latency target is p95 < 300 ms; the cumulative target is 3 s for 10
transitions on a developer laptop.

Marked `@pytest.mark.slow` so the default `pytest -q` run skips it.
Invoke explicitly with `pytest -m slow`.
"""

from __future__ import annotations

import datetime as dt
import time

import pytest

from admin_tui.core.changelist import _build_changelist
from admin_tui.core.request import build_request
from sample_project.library.models import Author, Book


PER_PAGE_TARGET = 0.3  # 300 ms p95
TOTAL_TARGET = 3.0     # 10 transitions × ~300 ms


@pytest.mark.slow
@pytest.mark.django_db
def test_100k_rows_page_transition_under_target(superuser):
    """Seed 100k books, then time 10 paginated calls to _build_changelist."""
    from django.contrib import admin

    author = Author.objects.create(name="Perf Author")
    objs = [
        Book(
            title=f"Book #{i:07d}",
            author=author,
            published=dt.date(2020, 1, 1),
            featured=False,
            archived=False,
            color="#000000",
            metadata={},
        )
        for i in range(100_000)
    ]
    Book.objects.bulk_create(objs, batch_size=5000)

    book_admin = admin.site._registry[Book]
    request = build_request(superuser)

    transitions = []
    for page in range(1, 11):
        request = build_request(superuser)
        t0 = time.perf_counter()
        cl = _build_changelist(book_admin, request, query={"p": page})
        # Force result-list materialisation so the timing reflects the
        # full transition cost an operator would see.
        list(cl.result_list)
        transitions.append(time.perf_counter() - t0)

    total = sum(transitions)
    # Sorted desc for p95.
    transitions_desc = sorted(transitions, reverse=True)
    # 10 samples → p95 is the worst sample.
    p95 = transitions_desc[0]

    print(f"\n100k changelist transitions: total {total:.2f}s, p95 {p95*1000:.0f}ms")
    print(f"  individual: {[f'{t*1000:.0f}ms' for t in transitions]}")

    assert total < TOTAL_TARGET, (
        f"10 page transitions took {total:.2f}s, target was {TOTAL_TARGET}s "
        f"(see SC-002)."
    )
    assert p95 < PER_PAGE_TARGET, (
        f"p95 page transition was {p95*1000:.0f}ms, target was "
        f"{PER_PAGE_TARGET*1000:.0f}ms (see SC-002)."
    )
