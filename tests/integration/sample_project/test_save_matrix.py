"""US3 — create/edit saves for every default field type (FR-012..014, SC-003).

The headline regression: many-to-many (and other multi-value) fields used to be
rendered with the single-value foreign-key Select and dropped on save. This
suite drives the Showcase add/edit forms through `ChangeScreen` and asserts that
every default widget/field type round-trips correctly, including M2M, and that
the right `LogEntry` is written.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.contrib.admin.models import ADDITION, CHANGE, LogEntry

from admin_tui._internal.session import TuiSession
from admin_tui.app import AdminTuiApp
from admin_tui.core.request import build_request
from admin_tui.screens.change import ChangeScreen
from admin_tui.sites import tui_site
from sample_project.library.models import Showcase


def _overlay_and_request(session, user):
    overlay = tui_site.get_or_synthesize(Showcase)
    request = build_request(user)
    request._tui_session = session
    return overlay, request


@pytest.mark.django_db
async def test_create_saves_all_field_types_including_m2m(superuser, showcase_targets):
    author = showcase_targets["author"]
    tags = showcase_targets["tags"]
    session = TuiSession(user=superuser, app_class=AdminTuiApp)
    async with AdminTuiApp(session=session).run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        overlay, request = _overlay_and_request(session, superuser)
        screen = ChangeScreen(
            session=session, overlay=overlay, request=request, obj=None, mode="add"
        )
        await pilot.app.push_screen(screen)
        await pilot.pause()

        w = screen._widgets
        w["title"].value = "Created Widget"
        # description is a TextField → multi-line TextArea (uses .text, not .value).
        w["description"].text = "A created description"
        w["status"].value = "published"
        w["is_active"].value = True
        w["author"].value = author.pk
        w["tags"].select_all()  # select every tag (the M2M regression case)
        w["quantity"].value = "7"
        w["price"].value = "3.50"

        screen.action_save()
        await pilot.pause()

        obj = Showcase.objects.get(title="Created Widget")
        assert obj.description == "A created description"
        assert obj.status == "published"
        assert obj.is_active is True
        assert obj.author_id == author.pk
        assert obj.quantity == 7
        assert obj.price == Decimal("3.50")
        # The M2M actually persisted (the bug: it used to be dropped).
        assert set(obj.tags.values_list("pk", flat=True)) == {t.pk for t in tags}

        # LogEntry: an ADDITION attributed to the session user.
        entry = LogEntry.objects.filter(object_id=str(obj.pk)).latest("id")
        assert entry.action_flag == ADDITION
        assert entry.user_id == superuser.pk


@pytest.mark.django_db
async def test_edit_updates_value_and_m2m(superuser, showcase_targets):
    tags = showcase_targets["tags"]
    obj = Showcase.objects.create(title="Editable", status="draft", quantity=1)
    obj.tags.set(tags[:1])

    session = TuiSession(user=superuser, app_class=AdminTuiApp)
    async with AdminTuiApp(session=session).run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        overlay, request = _overlay_and_request(session, superuser)
        # Re-fetch on this request so the form binds the right instance.
        instance = Showcase.objects.get(pk=obj.pk)
        screen = ChangeScreen(
            session=session, overlay=overlay, request=request, obj=instance, mode="edit"
        )
        await pilot.app.push_screen(screen)
        await pilot.pause()

        w = screen._widgets
        w["title"].value = "Edited Title"
        w["status"].value = "published"
        w["tags"].select_all()  # now all tags

        screen.action_save()
        await pilot.pause()

        obj.refresh_from_db()
        assert obj.title == "Edited Title"
        assert obj.status == "published"
        assert set(obj.tags.values_list("pk", flat=True)) == {t.pk for t in tags}

        entry = LogEntry.objects.filter(object_id=str(obj.pk)).latest("id")
        assert entry.action_flag == CHANGE
        assert entry.user_id == superuser.pk


@pytest.mark.django_db
async def test_text_field_renders_multiline_textarea(superuser, showcase_targets):
    """A model TextField (form CharField + Textarea widget) renders as a
    multi-line TextArea; a CharField stays a single-line Input. Multi-line
    content round-trips on save."""
    from textual.widgets import Input, TextArea

    session = TuiSession(user=superuser, app_class=AdminTuiApp)
    async with AdminTuiApp(session=session).run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        overlay, request = _overlay_and_request(session, superuser)
        screen = ChangeScreen(
            session=session, overlay=overlay, request=request, obj=None, mode="add"
        )
        await pilot.app.push_screen(screen)
        await pilot.pause()

        w = screen._widgets
        assert isinstance(w["description"], TextArea), type(w["description"])
        assert isinstance(w["title"], Input), type(w["title"])

        w["title"].value = "Multiline Widget"
        w["description"].text = "line one\nline two\nline three"
        w["status"].value = "draft"
        w["quantity"].value = "1"
        w["price"].value = "0.00"

        screen.action_save()
        await pilot.pause()

        obj = Showcase.objects.get(title="Multiline Widget")
        assert obj.description == "line one\nline two\nline three"


@pytest.mark.django_db
async def test_invalid_value_surfaces_error_and_does_not_save(superuser):
    session = TuiSession(user=superuser, app_class=AdminTuiApp)
    async with AdminTuiApp(session=session).run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        overlay, request = _overlay_and_request(session, superuser)
        screen = ChangeScreen(
            session=session, overlay=overlay, request=request, obj=None, mode="add"
        )
        await pilot.app.push_screen(screen)
        await pilot.pause()

        before = Showcase.objects.count()
        w = screen._widgets
        w["title"].value = "Bad Number"
        w["quantity"].value = "not-a-number"  # invalid for IntegerField

        screen.action_save()
        await pilot.pause()

        # Nothing saved; the screen is still mounted with a field error.
        assert Showcase.objects.count() == before
        assert screen.form is not None and not screen.form.is_valid()
        assert "quantity" in screen.form.errors
