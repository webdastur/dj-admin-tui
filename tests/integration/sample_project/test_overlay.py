"""End-to-end overlay coverage.

Every extension class has at least one assertion here. If any of
these break, the sample app fails.

The 7 extension classes:
  1. row_actions      — declarative slot + the bound action method.
  2. bulk_actions     — declarative slot + the bound action method.
  3. key_bindings     — declarative slot; bound to the changelist.
  4. render_cell      — per-column rendering override.
  5. field_widgets    — per-model widget override.
  6. get_detail_screen — full-screen replacement.
  7. before/after_save — lifecycle hooks.
Plus:
  - register_screen   — global tool-screen registration.
  - zero-config still works when overlays are unregistered.
  - Public API surface remains exactly 5 names.
"""

from __future__ import annotations

import datetime as dt
import importlib

import pytest

from dj_admin_tui._internal.public_api import _PUBLIC_NAMES
from dj_admin_tui.core.audit import _change_message, _log_addition, _log_change
from dj_admin_tui.core.forms import _build_form
from dj_admin_tui.core.request import build_request
from dj_admin_tui.sites import tui_site
from sample_project.library.models import Author, Book


@pytest.fixture
def with_library_overlays():
    """Reload `sample_project.library.tui` so the @register-decorated
    overlays + tui_site.register_screen call are in effect for the test.

    The other test files in this dir clear the registry per-test, so
    we restore from scratch here too.
    """
    tui_site._registry.clear()
    tui_site._synth_cache.clear()
    tui_site._screens.clear()
    # Reload the module — its module body re-runs the @register and
    # tui_site.register_screen calls.
    import sample_project.library.tui as tui_module

    importlib.reload(tui_module)
    yield
    tui_site._registry.clear()
    tui_site._synth_cache.clear()
    tui_site._screens.clear()


@pytest.fixture
def author(db):
    return Author.objects.create(name="Test Author", born=dt.date(1900, 1, 1))


@pytest.fixture
def featured_book(db, author):
    return Book.objects.create(
        title="Featured Title",
        author=author,
        published=dt.date(2025, 1, 1),
        featured=True,
        color="#FF0000",
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


# ---- 1, 3: row_actions + key_bindings ----------------------------


@pytest.mark.django_db
def test_book_overlay_declares_row_action(with_library_overlays):
    """Extension slot 1: row_actions = ["mark_featured_via_tui"]."""
    overlay = tui_site.get_or_synthesize(Book)
    assert "mark_featured_via_tui" in overlay.row_actions


@pytest.mark.django_db
def test_book_overlay_declares_key_binding(with_library_overlays):
    """Extension slot 3: key_bindings includes ('f', 'mark_featured_via_tui', 'Feature')."""
    overlay = tui_site.get_or_synthesize(Book)
    keys = [entry[0] for entry in overlay.key_bindings]
    assert "f" in keys
    matching = [e for e in overlay.key_bindings if e[0] == "f"]
    assert matching[0][1] == "mark_featured_via_tui"


@pytest.mark.django_db
def test_mark_featured_via_tui_action(with_library_overlays, db, author):
    """The row-action method actually does what it claims."""
    overlay = tui_site.get_or_synthesize(Book)
    request = build_request(_admin_user(db))
    book = Book.objects.create(
        title="Test",
        author=author,
        published=dt.date(2025, 1, 1),
        featured=False,
        color="#000000",
    )
    overlay.mark_featured_via_tui(request, book)
    book.refresh_from_db()
    assert book.featured is True


# ---- 2: bulk_actions --------------------------------------------


@pytest.mark.django_db
def test_book_overlay_declares_bulk_action(with_library_overlays):
    """Extension slot 2: bulk_actions = ["bulk_recolor"]."""
    overlay = tui_site.get_or_synthesize(Book)
    assert "bulk_recolor" in overlay.bulk_actions


@pytest.mark.django_db
def test_bulk_recolor_runs_against_queryset(with_library_overlays, db, author):
    overlay = tui_site.get_or_synthesize(Book)
    request = build_request(_admin_user(db))
    Book.objects.create(title="A", author=author, color="#000000")
    Book.objects.create(title="B", author=author, color="#000000")
    Book.objects.create(title="C", author=author, color="#000000")
    qs = Book.objects.all()
    overlay.bulk_recolor(request, qs)
    assert Book.objects.filter(color="#FF8800").count() == 3
    # message_user was called — captured in request._messages.captured.
    assert any("Recolored" in m for _l, m, _t in request._messages.captured)


# ---- 4: render_cell --------------------------------------------


@pytest.mark.django_db
def test_render_cell_override_bolds_featured_title(with_library_overlays, db, featured_book):
    overlay = tui_site.get_or_synthesize(Book)
    request = build_request(_admin_user(db))
    cell = overlay.render_cell(request, featured_book, "title")
    assert "bold yellow" in cell.display
    assert featured_book.title in cell.display


@pytest.mark.django_db
def test_render_cell_falls_through_to_default_for_other_fields(
    with_library_overlays, db, featured_book
):
    overlay = tui_site.get_or_synthesize(Book)
    request = build_request(_admin_user(db))
    cell = overlay.render_cell(request, featured_book, "author")
    # No special markup for non-title columns.
    assert "bold yellow" not in cell.display


# ---- 5: field_widgets ------------------------------------------


@pytest.mark.django_db
def test_color_field_widget_is_registered(with_library_overlays):
    """A ColorFormField bound field must resolve to the color picker factory."""
    from dj_admin_tui.widgets.registry import field_widgets
    from sample_project.library.fields import ColorFormField

    class _BF:
        field = ColorFormField()

        def value(self):
            return "#FF8800"

    factory = field_widgets.resolve(_BF())
    # We don't instantiate the widget (Textual needs an active App), but
    # the factory must come from our library module.
    assert factory.__module__ == "sample_project.library.tui"


# ---- 6: get_detail_screen --------------------------------------


@pytest.mark.django_db
def test_author_overlay_returns_custom_detail_screen(with_library_overlays):
    """Extension slot 6: AuthorTui.get_detail_screen → AuthorStatsScreen."""
    from sample_project.library.screens import AuthorStatsScreen

    overlay = tui_site.get_or_synthesize(Author)
    request = build_request(_admin_user_db())
    assert overlay.get_detail_screen(request) is AuthorStatsScreen


@pytest.mark.django_db
def test_book_overlay_still_uses_default_detail_screen(with_library_overlays):
    """Default routing still flows through get_detail_screen for un-overridden models."""
    from dj_admin_tui.screens.change import ChangeScreen

    overlay = tui_site.get_or_synthesize(Book)
    request = build_request(_admin_user_db())
    assert overlay.get_detail_screen(request) is ChangeScreen


# ---- 7: before_save / after_save -------------------------------


@pytest.mark.django_db
def test_before_save_populates_normalised_title(with_library_overlays, db, author):
    """Extension slot 7 (lifecycle hooks): before_save populates a field outside the form."""
    overlay = tui_site.get_or_synthesize(Book)
    request = build_request(_admin_user(db))
    _form, obj = _save_via_overlay_flow(
        overlay,
        request,
        data={
            "title": "MIXED Case TITLE",
            "author": str(author.pk),
            "published": "2025-01-01",
            "summary": "",
            "featured": "False",
            "archived": "False",
            "metadata": "{}",
            "color": "#000000",
            "tags": [],
        },
    )
    assert obj is not None
    obj.refresh_from_db()
    assert obj.normalised_title == "mixed case title"


@pytest.mark.django_db
def test_after_save_records_call(with_library_overlays, db, author):
    from sample_project.library.tui import BookTui

    BookTui._after_save_calls.clear()
    overlay = tui_site.get_or_synthesize(Book)
    request = build_request(_admin_user(db))
    _form, obj = _save_via_overlay_flow(
        overlay,
        request,
        data={
            "title": "After Save Tracker",
            "author": str(author.pk),
            "published": "2025-01-01",
            "summary": "",
            "featured": "False",
            "archived": "False",
            "metadata": "{}",
            "color": "#000000",
            "tags": [],
        },
    )
    assert obj is not None
    assert len(BookTui._after_save_calls) >= 1
    assert BookTui._after_save_calls[-1] == (obj.pk, True)


# ---- global tool screen + sites.register_screen --------------


@pytest.mark.django_db
def test_logs_tool_screen_is_registered(with_library_overlays):
    """sample_project/library/tui.py calls tui_site.register_screen("logs", LogEntryScreen)."""
    from sample_project.library.screens import LogEntryScreen

    assert "logs" in tui_site._screens
    assert tui_site._screens["logs"] is LogEntryScreen


# ---- zero-config still works -----------------------


@pytest.mark.django_db
def test_unregistering_overlays_falls_back_to_default(with_library_overlays):
    """Remove the explicit overlays — Book and Author still render fully via
    the synthesized default."""
    tui_site.unregister(Book)
    tui_site.unregister(Author)
    request = build_request(_admin_user_db())
    book_overlay = tui_site.get_or_synthesize(Book)
    author_overlay = tui_site.get_or_synthesize(Author)
    # The synthesized overlays must be plain TuiAdmin (or subclass)
    # carrying the live ModelAdmin.
    from dj_admin_tui.options import TuiAdmin

    assert isinstance(book_overlay, TuiAdmin)
    assert isinstance(author_overlay, TuiAdmin)
    # And the changelist API still resolves columns.
    cols = book_overlay.get_list_columns(request)
    assert "title" in cols


# ---- public API surface unchanged ---------


@pytest.mark.django_db
def test_public_api_surface_unchanged_after_overlay_load(with_library_overlays):
    """Loading the sample overlays MUST NOT add anything to dj_admin_tui.__all__."""
    import dj_admin_tui

    assert set(dj_admin_tui.__all__) == set(_PUBLIC_NAMES)


# ---- helpers ---------------------------------------------


def _admin_user_db():
    """Lazily create / fetch a superuser for tests not parameterized on `superuser`."""
    from django.contrib.auth import get_user_model

    U = get_user_model()
    user, _ = U.objects.get_or_create(
        username="overlay_test_admin",
        defaults={
            "is_superuser": True,
            "is_staff": True,
            "is_active": True,
        },
    )
    return user


def _admin_user(db):
    return _admin_user_db()
