"""Lifecycle hook contract (extension slot 7), isolated from end-to-end UI flow.

Complements test_overlay.py's end-to-end coverage with focused, ordering-
specific assertions:

  (a) before_save fires exactly once per save with the correct `created` flag.
  (b) after_save fires AFTER log_addition / log_change (assert via LogEntry
      count snapshots).
  (c) before_action fires before func(...) and after_action fires after,
      receiving the captured messages in `result`.
  (d) On action exception, after_action's success branch is NOT called
      (covered at the hook-contract level rather than the
      _run_action level).
"""

from __future__ import annotations

import datetime as dt

import pytest
from django.contrib.admin.models import LogEntry

from dj_admin_tui.core.actions import _run_action
from dj_admin_tui.core.audit import _change_message, _log_addition, _log_change
from dj_admin_tui.core.forms import _build_form
from dj_admin_tui.core.request import build_request
from dj_admin_tui.options import TuiAdmin
from dj_admin_tui.sites import tui_site
from sample_project.library.models import Author, Book


@pytest.fixture(autouse=True)
def _reset_tui_site():
    tui_site._registry.clear()
    tui_site._synth_cache.clear()
    return


@pytest.fixture
def author(db):
    return Author.objects.create(name="Test Author")


@pytest.fixture
def existing_book(db, author):
    return Book.objects.create(
        title="Old Title",
        author=author,
        published=dt.date(2025, 1, 1),
        color="#000000",
    )


def _save_via_overlay_flow(overlay, request, *, obj=None, data):
    """Mirror ChangeScreen.action_save() at the call-path level."""
    is_add = obj is None
    form = _build_form(overlay.model_admin, request, obj=obj, data=data)
    if not form.is_valid():
        return form, None
    new_obj = form.save(commit=False)
    overlay.before_save(request, new_obj, created=is_add)
    overlay.model_admin.save_model(request, new_obj, form, change=not is_add)
    overlay.model_admin.save_related(request, form, [], change=not is_add)
    msg = _change_message(overlay.model_admin, request, form, [], add=is_add)
    if is_add:
        _log_addition(overlay.model_admin, request, new_obj, msg)
    else:
        _log_change(overlay.model_admin, request, new_obj, msg)
    overlay.after_save(request, new_obj, created=is_add)
    return form, new_obj


# ---- (a) before_save firing + created flag -----------------------


@pytest.mark.django_db
def test_before_save_receives_created_true_on_add(superuser, author):
    sequence: list[tuple[str, bool]] = []

    class SeqOverlay(TuiAdmin):
        def before_save(self, request, obj, *, created):
            sequence.append(("before_save", created))

        def after_save(self, request, obj, *, created):
            sequence.append(("after_save", created))

    tui_site.register(Book, SeqOverlay)
    overlay = tui_site.get_or_synthesize(Book)
    request = build_request(superuser)
    _save_via_overlay_flow(
        overlay,
        request,
        data={
            "title": "Create-Mode Test",
            "author": str(author.pk),
            "published": "2026-01-01",
            "summary": "",
            "featured": "False",
            "archived": "False",
            "metadata": "{}",
            "color": "#000000",
            "tags": [],
        },
    )
    assert sequence == [("before_save", True), ("after_save", True)]


@pytest.mark.django_db
def test_before_save_receives_created_false_on_edit(superuser, existing_book):
    sequence: list[tuple[str, bool]] = []

    class SeqOverlay(TuiAdmin):
        def before_save(self, request, obj, *, created):
            sequence.append(("before_save", created))

        def after_save(self, request, obj, *, created):
            sequence.append(("after_save", created))

    tui_site.register(Book, SeqOverlay)
    overlay = tui_site.get_or_synthesize(Book)
    request = build_request(superuser)
    _save_via_overlay_flow(
        overlay,
        request,
        obj=existing_book,
        data={
            "title": "Edit-Mode Test",
            "author": str(existing_book.author_id),
            "published": existing_book.published.isoformat(),
            "summary": "",
            "featured": "False",
            "archived": "False",
            "metadata": "{}",
            "color": "#000000",
            "tags": [],
        },
    )
    assert sequence == [("before_save", False), ("after_save", False)]


# ---- (b) after_save fires after log_addition / log_change --------


@pytest.mark.django_db
def test_after_save_fires_after_log_addition(superuser, author):
    log_counts_seen: list[int] = []

    class CountOverlay(TuiAdmin):
        def after_save(self, request, obj, *, created):
            log_counts_seen.append(LogEntry.objects.count())

    tui_site.register(Book, CountOverlay)
    overlay = tui_site.get_or_synthesize(Book)
    request = build_request(superuser)

    initial = LogEntry.objects.count()
    _save_via_overlay_flow(
        overlay,
        request,
        data={
            "title": "Order-Of-Hooks Test",
            "author": str(author.pk),
            "published": "2026-01-01",
            "summary": "",
            "featured": "False",
            "archived": "False",
            "metadata": "{}",
            "color": "#000000",
            "tags": [],
        },
    )
    # When after_save fired, the LogEntry had already been written →
    # observed count strictly greater than the pre-save count.
    assert log_counts_seen == [initial + 1]


# ---- (c) before/after_action ordering -----------------------------


@pytest.mark.django_db
def test_before_action_fires_before_after_action_on_success(superuser, author):
    sequence: list[str] = []

    class ActionSeqOverlay(TuiAdmin):
        def before_action(self, request, action, queryset):
            sequence.append("before")

        def after_action(self, request, action, queryset, *, result=None):
            sequence.append("after")

    tui_site.register(Book, ActionSeqOverlay)
    overlay = tui_site.get_or_synthesize(Book)
    Book.objects.create(title="Action Test", author=author, color="#000000")
    request = build_request(superuser)
    queryset = Book.objects.all()
    _run_action(overlay, request, "mark_featured_action", queryset)
    assert sequence == ["before", "after"]


@pytest.mark.django_db
def test_after_action_receives_result_kwarg(superuser, author):
    seen_result: list = []

    class ResultOverlay(TuiAdmin):
        def after_action(self, request, action, queryset, *, result=None):
            seen_result.append(result)

    tui_site.register(Book, ResultOverlay)
    overlay = tui_site.get_or_synthesize(Book)
    Book.objects.create(title="Test", author=author, color="#000000")
    request = build_request(superuser)
    _run_action(overlay, request, "mark_featured_action", Book.objects.all())
    # The mark_featured_action returns None, but the kwarg was passed.
    assert seen_result == [None]


# ---- (d) on action exception, after_action NOT called -----------


@pytest.mark.django_db
def test_after_action_not_called_on_exception(superuser, author):
    sequence: list[str] = []

    class FailureOverlay(TuiAdmin):
        def before_action(self, request, action, queryset):
            sequence.append("before")

        def after_action(self, request, action, queryset, *, result=None):
            sequence.append("after_SHOULD_NOT_FIRE")

    tui_site.register(Book, FailureOverlay)
    overlay = tui_site.get_or_synthesize(Book)
    Book.objects.create(title="Fail Test", author=author, color="#000000")
    request = build_request(superuser)
    result = _run_action(overlay, request, "failing_action", Book.objects.all())
    assert result.exception is not None
    assert sequence == ["before"]  # after_action NOT in the sequence
