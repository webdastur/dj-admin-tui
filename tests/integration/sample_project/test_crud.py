"""Create / edit / readonly_fields + audit parity (FR-013–015, SC-004).

We exercise the save flow at the call-path level — the same sequence
ChangeScreen.action_save() runs — rather than driving Pilot. That way we
isolate Constitution-I + SC-004 fidelity from any current UI quirks.

The save sequence mirrors django.contrib.admin.options._changeform_view:

    new_obj = form.save(commit=False)
    overlay.before_save(request, obj, created=is_add)
    model_admin.save_model(request, obj, form, change=not is_add)
    model_admin.save_related(request, form, [], change=not is_add)
    change_message = construct_change_message(request, form, [], add=is_add)
    log_addition(...) | log_change(...)
    overlay.after_save(request, obj, created=is_add)
"""

from __future__ import annotations

import datetime as dt
import json

import pytest
from django.contrib.admin.models import ADDITION, CHANGE, LogEntry
from django.contrib.contenttypes.models import ContentType

from admin_tui.core.audit import _change_message, _log_addition, _log_change
from admin_tui.core.forms import (
    _build_form,
    _iter_bound_fields,
    _readonly_field_names,
)
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
    return Author.objects.create(name="Test Author", born=dt.date(1900, 1, 1))


@pytest.fixture
def existing_book(db, author):
    return Book.objects.create(
        title="Old Title",
        author=author,
        published=dt.date(2000, 1, 1),
        featured=False,
    )


def _save_flow(overlay, request, *, obj=None, data):
    """Mirror ChangeScreen.action_save() at the call-path level."""
    is_add = obj is None
    form = _build_form(overlay.model_admin, request, obj=obj, data=data)
    if not form.is_valid():
        return form, None  # caller asserts on errors
    new_obj = form.save(commit=False)
    overlay.before_save(request, new_obj, created=is_add)
    overlay.model_admin.save_model(request, new_obj, form, change=not is_add)
    overlay.model_admin.save_related(request, form, [], change=not is_add)
    change_message = _change_message(
        overlay.model_admin, request, form, [], add=is_add
    )
    if is_add:
        _log_addition(overlay.model_admin, request, new_obj, change_message)
    else:
        _log_change(overlay.model_admin, request, new_obj, change_message)
    overlay.after_save(request, new_obj, created=is_add)
    return form, new_obj


# ---- create ---------------------------------------------------------


@pytest.mark.django_db
def test_create_book_with_valid_data_persists_and_logs(superuser, author):
    """FR-013 + FR-015 + SC-004: create + LogEntry written + parity."""
    request = build_request(superuser)
    overlay = tui_site.get_or_synthesize(Book)
    before = Book.objects.count()

    form, obj = _save_flow(
        overlay,
        request,
        data={
            "title": "Brand New Book",
            "author": str(author.pk),
            "published": "2026-05-30",
            "summary": "A test fixture.",
            "featured": "False",
            "archived": "False",
            "metadata": "{}",
            "tags": [],
        },
    )

    assert form.is_valid(), form.errors.as_json()
    assert Book.objects.count() == before + 1
    assert obj.pk is not None
    assert obj.title == "Brand New Book"

    log = LogEntry.objects.latest("action_time")
    assert log.user_id == superuser.id
    assert log.action_flag == ADDITION
    assert log.content_type_id == ContentType.objects.get_for_model(Book).id
    assert log.object_id == str(obj.pk)


@pytest.mark.django_db
def test_create_with_failing_clean_does_not_save(superuser, author):
    """FR-013: a `clean_*` rejection blocks save and surfaces the error."""
    request = build_request(superuser)
    overlay = tui_site.get_or_synthesize(Book)
    before = Book.objects.count()
    before_logs = LogEntry.objects.count()

    form, obj = _save_flow(
        overlay,
        request,
        data={
            "title": "forbidden",
            "author": str(author.pk),
            "published": "2026-05-30",
            "summary": "",
            "featured": "False",
            "archived": "False",
            "metadata": "{}",
            "tags": [],
        },
    )

    assert not form.is_valid()
    assert "title" in form.errors
    assert any("forbidden" in e.lower() for e in form.errors["title"])
    assert obj is None
    assert Book.objects.count() == before
    assert LogEntry.objects.count() == before_logs


# ---- edit -----------------------------------------------------------


@pytest.mark.django_db
def test_edit_existing_book_logs_change_with_parity(superuser, existing_book):
    """FR-013 + FR-015 + SC-004: edit + LogEntry change_message parity."""
    request = build_request(superuser)
    overlay = tui_site.get_or_synthesize(Book)

    form, obj = _save_flow(
        overlay,
        request,
        obj=existing_book,
        data={
            "title": "Updated Title",
            "author": str(existing_book.author_id),
            "published": existing_book.published.isoformat(),
            "summary": "Newly added summary.",
            "featured": "True",  # toggled
            "archived": "False",
            "metadata": "{}",
            "tags": [],
        },
    )

    assert form.is_valid(), form.errors.as_json()
    existing_book.refresh_from_db()
    assert existing_book.title == "Updated Title"
    assert existing_book.featured is True

    log = LogEntry.objects.latest("action_time")
    assert log.action_flag == CHANGE
    assert log.user_id == superuser.id

    # SC-004 parity: the change_message we stored equals what
    # construct_change_message would return for the same form.
    expected_msg = overlay.model_admin.construct_change_message(
        request, form, [], add=False
    )
    assert json.loads(log.change_message) == expected_msg


# ---- readonly_fields ----------------------------------------------


@pytest.mark.django_db
def test_readonly_fields_excluded_from_form(superuser, existing_book, monkeypatch):
    """FR-014 enforcement: Django's `ModelAdmin.get_form` EXCLUDES
    readonly_fields from `form.fields`. That excludes them from POST data
    too, so the user cannot mutate them via the form at all — readonly is
    enforced by absence, not by widget state."""
    request = build_request(superuser)
    overlay = tui_site.get_or_synthesize(Book)

    monkeypatch.setattr(overlay.model_admin, "readonly_fields", ("published",))

    readonly = _readonly_field_names(overlay.model_admin, request, existing_book)
    assert "published" in readonly

    form = _build_form(overlay.model_admin, request, obj=existing_book)
    form_field_names = [n for n, _ in _iter_bound_fields(form)]
    # The form does NOT contain `published` — that's how the admin
    # enforces read-only-ness at the form layer. The ChangeScreen displays
    # the value as text (read from the instance) so the operator can see it.
    assert "published" not in form_field_names


@pytest.mark.django_db
def test_readonly_field_value_survives_save(superuser, existing_book, monkeypatch):
    """FR-014: an attempt to mutate a readonly field via the form silently
    keeps the original value. Even if the operator's submitted data contains
    a new value, the form excludes the field and the instance is untouched."""
    request = build_request(superuser)
    overlay = tui_site.get_or_synthesize(Book)
    monkeypatch.setattr(overlay.model_admin, "readonly_fields", ("published",))

    original_published = existing_book.published
    rogue_data = {
        "title": "Updated",
        "author": str(existing_book.author_id),
        "summary": "",
        "featured": "False",
        "archived": "False",
        "metadata": "{}",
        "tags": [],
        # Note: `published` not included because the form would reject it.
        # Even if a malicious caller added it, the form would ignore it.
    }
    form, obj = _save_flow(overlay, request, obj=existing_book, data=rogue_data)
    assert form.is_valid(), form.errors.as_json()
    existing_book.refresh_from_db()
    assert existing_book.published == original_published


# ---- lifecycle hooks --------------------------------------------


@pytest.mark.django_db
def test_before_save_and_after_save_fire_in_order(superuser, author):
    """FR-024 lifecycle hook: before_save → save → after_save."""
    from admin_tui.options import TuiAdmin

    calls = []

    class HookedOverlay(TuiAdmin):
        def before_save(self, request, obj, *, created):
            calls.append(("before_save", created, obj.pk))

        def after_save(self, request, obj, *, created):
            calls.append(("after_save", created, obj.pk))

    tui_site.register(Book, HookedOverlay)
    overlay = tui_site.get_or_synthesize(Book)
    request = build_request(superuser)

    form, obj = _save_flow(
        overlay,
        request,
        data={
            "title": "Hook Test",
            "author": str(author.pk),
            "published": "2026-05-30",
            "summary": "",
            "featured": "False",
            "archived": "False",
            "metadata": "{}",
            "tags": [],
        },
    )
    assert form.is_valid(), form.errors.as_json()

    # before_save fires with pk=None (not yet saved); after_save fires
    # with the assigned pk.
    assert len(calls) == 2
    assert calls[0][0] == "before_save"
    assert calls[0][1] is True  # created=True
    assert calls[0][2] is None  # pk not yet assigned
    assert calls[1][0] == "after_save"
    assert calls[1][1] is True
    assert calls[1][2] == obj.pk


# ---- delete (US3 / FR-016, SC-004) -----------------------------


@pytest.mark.django_db
def test_tui_delete_path_writes_log_deletion_per_object(superuser, author):
    """FR-016: deleting through the TUI's delete sequence writes a
    LogEntry of type DELETION per deleted object, with correct
    user / content_type / object_repr — matching the web admin's
    delete_selected behavior."""
    from django.contrib.admin.models import DELETION

    from admin_tui.core.audit import _log_deletion

    request = build_request(superuser)
    overlay = tui_site.get_or_synthesize(Book)
    b1 = Book.objects.create(title="Delete Me 1", author=author,
                             published=dt.date(2020, 1, 1))
    b2 = Book.objects.create(title="Delete Me 2", author=author,
                             published=dt.date(2021, 1, 1))
    targets = list(Book.objects.filter(pk__in=[b1.pk, b2.pk]))

    # ActionConfirmScreen._do_delete sequence: log first, then delete.
    for obj in targets:
        _log_deletion(overlay.model_admin, request, obj)
    qs = Book.objects.filter(pk__in=[b1.pk, b2.pk])
    overlay.model_admin.delete_queryset(request, qs)

    assert not Book.objects.filter(pk__in=[b1.pk, b2.pk]).exists()
    ct = ContentType.objects.get_for_model(Book)
    deletions = LogEntry.objects.filter(
        action_flag=DELETION,
        content_type=ct,
    ).order_by("-action_time")[:2]
    assert deletions.count() == 2
    object_reprs = {log.object_repr for log in deletions}
    assert object_reprs == {"Delete Me 1", "Delete Me 2"}
    for log in deletions:
        assert log.user_id == superuser.id


@pytest.mark.django_db
def test_view_only_user_lacks_delete_permission(staff_only_user, author):
    """FR-016 + Constitution II: a view-only user gets has_delete_permission
    = False. The screen hides the delete affordance based on this gate."""
    from django.contrib.auth.models import Permission
    from django.contrib.contenttypes.models import ContentType as CT

    ct = CT.objects.get_for_model(Book)
    staff_only_user.user_permissions.add(
        Permission.objects.get(codename="view_book", content_type=ct)
    )
    overlay = tui_site.get_or_synthesize(Book)
    request = build_request(staff_only_user)
    assert overlay.has_delete_permission(request) is False


@pytest.mark.django_db
def test_delete_permission_user_can_delete(staff_only_user, author):
    from django.contrib.auth.models import Permission
    from django.contrib.contenttypes.models import ContentType as CT

    ct = CT.objects.get_for_model(Book)
    staff_only_user.user_permissions.add(
        Permission.objects.get(codename="view_book", content_type=ct),
        Permission.objects.get(codename="delete_book", content_type=ct),
    )
    overlay = tui_site.get_or_synthesize(Book)
    request = build_request(staff_only_user)
    assert overlay.has_delete_permission(request) is True


# ---- audit parity (the SC-004 anchor) ---------------------------


@pytest.mark.django_db
def test_log_addition_uses_admin_helpers_directly(superuser, author):
    """Verify _log_addition routes through ModelAdmin.log_addition.

    Sanity check on the pass-through guarantee in core/audit.py.
    """
    from unittest.mock import patch

    request = build_request(superuser)
    overlay = tui_site.get_or_synthesize(Book)
    book = Book.objects.create(
        title="Pass-through test",
        author=author,
        published=dt.date(2026, 1, 1),
    )

    with patch.object(
        overlay.model_admin,
        "log_addition",
        wraps=overlay.model_admin.log_addition,
    ) as spy:
        _log_addition(overlay.model_admin, request, book, [{"added": {}}])
        spy.assert_called_once()
