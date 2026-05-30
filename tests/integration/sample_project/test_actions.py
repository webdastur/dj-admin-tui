"""Admin actions + FR-019 error path (FR-017, FR-018, FR-019, SC-004).

We exercise `_run_action` at the call-path level. The contract:

  * On success, ActionResult.exception is None, messages captured,
    after_action fires with the action's return value.
  * On Exception, ActionResult.exception holds it, messages emitted
    before the raise ARE captured, after_action's success branch does
    NOT fire, no LogEntry is written for the failed work.

The Pilot-driven integration (the UI flow through ChangelistScreen +
ActionConfirmScreen) is exercised by the existing Phase 3 boot smoke
test + targeted Phase 5 selection tests below.
"""

from __future__ import annotations

import datetime as dt

import pytest
from django.contrib.admin.models import LogEntry
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

from admin_tui.core.actions import ActionResult, _get_actions, _run_action
from admin_tui.core.request import build_request
from admin_tui.sites import tui_site
from sample_project.library.models import Author, Book


@pytest.fixture(autouse=True)
def _reset_tui_site():
    tui_site._registry.clear()
    tui_site._synth_cache.clear()
    yield


@pytest.fixture
def author(db):
    return Author.objects.create(name="Test Author")


@pytest.fixture
def three_books(db, author):
    books = [
        Book.objects.create(
            title=f"Book {i}",
            author=author,
            published=dt.date(2000 + i, 1, 1),
            featured=False,
        )
        for i in range(3)
    ]
    return Book.objects.filter(pk__in=[b.pk for b in books])


# ---- mark_featured (success path) ---------------------------------


@pytest.mark.django_db
def test_mark_featured_action_updates_and_messages(superuser, three_books):
    """FR-017 + FR-018: action runs, message_user output captured."""
    request = build_request(superuser)
    overlay = tui_site.get_or_synthesize(Book)

    result = _run_action(
        overlay, request, "mark_featured_action", three_books
    )

    assert isinstance(result, ActionResult)
    assert result.exception is None
    # All 3 books are featured.
    assert Book.objects.filter(pk__in=three_books, featured=True).count() == 3
    # The action's message_user call is captured.
    assert len(result.messages) == 1
    level, message, _tags = result.messages[0]
    assert "3 book(s) were updated" in message


# ---- failing_action (FR-019 error path) ---------------------------


@pytest.mark.django_db
def test_failing_action_captures_pre_raise_messages_and_skips_after_action(
    superuser, three_books
):
    """FR-019: emits a message, raises, no LogEntry written, after_action
    does NOT fire."""
    from admin_tui.options import TuiAdmin

    after_action_fired = False

    class SpyOverlay(TuiAdmin):
        def after_action(self, request, action, queryset, *, result=None):
            nonlocal after_action_fired
            after_action_fired = True

    tui_site.register(Book, SpyOverlay)
    overlay = tui_site.get_or_synthesize(Book)
    request = build_request(superuser)

    logs_before = LogEntry.objects.count()
    result = _run_action(overlay, request, "failing_action", three_books)

    assert isinstance(result.exception, RuntimeError)
    assert "boom" in str(result.exception)
    # The "starting…" message emitted BEFORE the raise is captured.
    assert any("starting" in m for _l, m, _t in result.messages)
    # after_action was NOT called on the exception branch.
    assert after_action_fired is False
    # No LogEntry claiming success was written by _run_action.
    assert LogEntry.objects.count() == logs_before


@pytest.mark.django_db
def test_after_action_fires_on_success_branch(superuser, three_books):
    """Counterpart to the FR-019 test: success branch DOES fire after_action."""
    from admin_tui.options import TuiAdmin

    fired_with: dict = {}

    class SpyOverlay(TuiAdmin):
        def after_action(self, request, action, queryset, *, result=None):
            fired_with["action"] = action
            fired_with["result"] = result

    tui_site.register(Book, SpyOverlay)
    overlay = tui_site.get_or_synthesize(Book)
    request = build_request(superuser)

    _run_action(overlay, request, "mark_featured_action", three_books)
    assert fired_with["action"] == "mark_featured_action"


@pytest.mark.django_db
def test_before_action_fires_unconditionally(superuser, three_books):
    """before_action fires even when the action raises (per the task spec)."""
    from admin_tui.options import TuiAdmin

    before_action_fired = False

    class SpyOverlay(TuiAdmin):
        def before_action(self, request, action, queryset):
            nonlocal before_action_fired
            before_action_fired = True

    tui_site.register(Book, SpyOverlay)
    overlay = tui_site.get_or_synthesize(Book)
    request = build_request(superuser)

    _run_action(overlay, request, "failing_action", three_books)
    assert before_action_fired is True


# ---- permission filtering -----------------------------------------


@pytest.mark.django_db
def test_get_actions_filters_for_view_only_user(staff_only_user, three_books):
    """A view-only user sees no change-required actions in get_actions.

    The admin actions are declared with `permissions=["change"]`, which
    `ModelAdmin.get_actions` filters on. We don't second-guess that gate.
    """
    # Grant view-only on Book.
    ct = ContentType.objects.get_for_model(Book)
    staff_only_user.user_permissions.add(
        Permission.objects.get(codename="view_book", content_type=ct)
    )
    overlay = tui_site.get_or_synthesize(Book)
    request = build_request(staff_only_user)

    actions = _get_actions(overlay, request)
    # `mark_featured_action`, `archive_selected_action`, `failing_action`
    # all require `change`. They MUST NOT be available to a view-only user.
    assert "mark_featured_action" not in actions
    assert "archive_selected_action" not in actions
    assert "failing_action" not in actions


@pytest.mark.django_db
def test_get_actions_returns_change_actions_for_change_perm_user(
    staff_only_user, three_books
):
    ct = ContentType.objects.get_for_model(Book)
    staff_only_user.user_permissions.add(
        Permission.objects.get(codename="change_book", content_type=ct),
        Permission.objects.get(codename="view_book", content_type=ct),
    )
    overlay = tui_site.get_or_synthesize(Book)
    request = build_request(staff_only_user)

    actions = _get_actions(overlay, request)
    assert "mark_featured_action" in actions
    assert "archive_selected_action" in actions


# ---- unknown / missing action ------------------------------------


@pytest.mark.django_db
def test_run_action_raises_keyerror_for_unknown_action(superuser, three_books):
    overlay = tui_site.get_or_synthesize(Book)
    request = build_request(superuser)
    with pytest.raises(KeyError, match="not available"):
        _run_action(overlay, request, "no_such_action", three_books)
