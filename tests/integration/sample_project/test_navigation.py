"""End-to-end TUI navigation via Pilot.

Drives the actual TUI through the operator's expected flows against the
live ORM. These would have caught the four integration bugs fixed in
commit 8a46640 — none of which the contract-level Phase 1-7 tests hit
because their Pilot coverage stopped at IndexScreen.on_mount:

  1. ChangelistScreen.self.query : dict shadowed Textual's Screen.query()
     DOM method → TypeError on push_screen → caught here by
     `test_index_to_changelist_navigation`.
  2. Django's SynchronousOnlyOperation blocked ORM calls in Textual's
     async event loop → caught by every test below that hits the DB,
     because the AdminTuiApp constructor now opts out of the guard.
  3. Screen.bind() doesn't exist in Textual 8.x → caught by
     `test_overlay_key_binding_fires_on_row`.
  4. DataTable swallows Enter and emits RowSelected → caught by
     `test_enter_on_row_opens_detail`.

These tests fix the package's reliance on contract-only assertions —
contracts pin the right *signatures*, but only Pilot proves the
*runtime* assembly works.
"""

from __future__ import annotations

import datetime as dt
import importlib

import pytest

from admin_tui._internal.session import TuiSession
from admin_tui.app import AdminTuiApp
from admin_tui.screens.change import ChangeScreen
from admin_tui.screens.changelist import ChangelistScreen
from admin_tui.screens.index import IndexScreen
from admin_tui.sites import tui_site
from sample_project.library.models import Author, Book


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

    Uses `transactional_db` (not `db`) because Pilot runs the App in a
    worker thread, and Django's thread-local connections + SQLite's
    default journal mode would deadlock if we held a write transaction
    in the main thread while the App thread reads the same tables.
    transactional_db commits to the test DB so cross-connection reads
    work.
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
    # Materialise to a list so Pilot's async-context queries don't have to
    # share the cursor with a lazy queryset.
    return list(Book.objects.all())


def _find_model_row_index(list_view, model_name: str) -> int:
    """Return the index of the row representing `model_name` in the index ListView."""
    for i, child in enumerate(list_view.children):
        if hasattr(child, "model") and child.model.__name__ == model_name:
            return i
    raise AssertionError(f"{model_name} not present in index ListView")


async def _navigate_index_to(pilot, model_name: str) -> None:
    """Drive arrow keys + Enter on the IndexScreen to open `model_name`'s changelist."""
    from textual.widgets import ListView

    list_view = pilot.app.screen.query_one("#index-list", ListView)
    idx = _find_model_row_index(list_view, model_name)
    # ListView starts with no highlight; first `down` highlights index 0.
    await pilot.press("down")
    for _ in range(idx):
        await pilot.press("down")
    await pilot.press("enter")
    await pilot.pause()


# ---------------------------------------------------------------------
# Boot + navigation
# ---------------------------------------------------------------------


@pytest.mark.django_db
async def test_app_boots_and_index_mounts(superuser, with_overlays):
    """Sanity: the App constructs and IndexScreen is the active screen."""
    session = TuiSession(user=superuser, app_class=AdminTuiApp)
    async with AdminTuiApp(session=session).run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        assert isinstance(pilot.app.screen, IndexScreen)


@pytest.mark.django_db
async def test_index_lists_seeded_models(superuser, seeded_books, with_overlays):
    """IndexScreen.populate finds Book / Author / Tag / Note in the listing."""
    from textual.widgets import ListView

    session = TuiSession(user=superuser, app_class=AdminTuiApp)
    async with AdminTuiApp(session=session).run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        list_view = pilot.app.screen.query_one("#index-list", ListView)
        models = {
            c.model.__name__ for c in list_view.children if hasattr(c, "model")
        }
        assert {"Book", "Author", "Tag", "Note"}.issubset(models)


@pytest.mark.django_db
async def test_index_to_changelist_navigation(
    superuser, seeded_books, with_overlays
):
    """Pushing ChangelistScreen must NOT raise (bug 1: Screen.query shadowing).

    Also exercises bug 2 (SynchronousOnlyOperation): the ChangelistScreen's
    on_mount calls _build_changelist which hits get_changelist_instance.
    """
    session = TuiSession(user=superuser, app_class=AdminTuiApp)
    async with AdminTuiApp(session=session).run_test(size=(140, 40)) as pilot:
        await pilot.pause()
        await _navigate_index_to(pilot, "Book")
        assert isinstance(pilot.app.screen, ChangelistScreen)
        assert pilot.app.screen.overlay.model_admin.model is Book


# ---------------------------------------------------------------------
# ChangelistScreen rendering + behaviour
# ---------------------------------------------------------------------


@pytest.mark.django_db
async def test_changelist_renders_seeded_rows(
    superuser, seeded_books, with_overlays
):
    """The DataTable populates with the seeded rows after on_mount."""
    from textual.widgets import DataTable

    session = TuiSession(user=superuser, app_class=AdminTuiApp)
    async with AdminTuiApp(session=session).run_test(size=(140, 40)) as pilot:
        await pilot.pause()
        await _navigate_index_to(pilot, "Book")
        table = pilot.app.screen.query_one("#changelist-table", DataTable)
        # Selection column + the 5 BookAdmin.list_display columns.
        assert len(table.columns) == 6
        assert table.row_count == 4


@pytest.mark.django_db
async def test_search_narrows_changelist(
    superuser, seeded_books, with_overlays
):
    """`/` opens search modal; submitting 'Tolkien' narrows to 2 rows."""
    from textual.widgets import DataTable, Input

    session = TuiSession(user=superuser, app_class=AdminTuiApp)
    async with AdminTuiApp(session=session).run_test(size=(140, 40)) as pilot:
        await pilot.pause()
        await _navigate_index_to(pilot, "Book")
        await pilot.press("slash")
        await pilot.pause()
        # The search modal is now active.
        pilot.app.screen.query_one(Input).value = "Tolkien"
        await pilot.press("enter")
        await pilot.pause()
        table = pilot.app.screen.query_one("#changelist-table", DataTable)
        assert table.row_count == 2


@pytest.mark.django_db
async def test_enter_on_row_opens_detail(
    superuser, seeded_books, with_overlays
):
    """Bug 4: DataTable.RowSelected → action_open_detail → ChangeScreen mounted."""
    session = TuiSession(user=superuser, app_class=AdminTuiApp)
    async with AdminTuiApp(session=session).run_test(size=(140, 40)) as pilot:
        await pilot.pause()
        await _navigate_index_to(pilot, "Book")
        await pilot.press("enter")
        await pilot.pause()
        assert isinstance(pilot.app.screen, ChangeScreen)
        assert pilot.app.screen.mode == "view"
        assert pilot.app.screen.obj is not None


@pytest.mark.django_db
async def test_space_toggles_multi_select(
    superuser, seeded_books, with_overlays
):
    """Space toggles a row's selection; selected_pks reflects state."""
    session = TuiSession(user=superuser, app_class=AdminTuiApp)
    async with AdminTuiApp(session=session).run_test(size=(140, 40)) as pilot:
        await pilot.pause()
        await _navigate_index_to(pilot, "Book")
        screen = pilot.app.screen
        assert isinstance(screen, ChangelistScreen)
        assert len(screen.selected_pks) == 0
        await pilot.press("space")
        await pilot.pause()
        assert len(screen.selected_pks) == 1
        await pilot.press("down")
        await pilot.press("space")
        await pilot.pause()
        assert len(screen.selected_pks) == 2
        # Toggle the first off again.
        await pilot.press("up")
        await pilot.press("space")
        await pilot.pause()
        assert len(screen.selected_pks) == 1


@pytest.mark.django_db
async def test_x_opens_action_picker_modal(
    superuser, seeded_books, with_overlays
):
    """`x` after at least one selection opens the action picker."""
    from admin_tui.screens.changelist import _ActionPickerModal

    session = TuiSession(user=superuser, app_class=AdminTuiApp)
    async with AdminTuiApp(session=session).run_test(size=(140, 40)) as pilot:
        await pilot.pause()
        await _navigate_index_to(pilot, "Book")
        await pilot.press("space")
        await pilot.pause()
        await pilot.press("x")
        await pilot.pause()
        assert isinstance(pilot.app.screen, _ActionPickerModal)


@pytest.mark.django_db
async def test_x_with_no_selection_does_not_open_picker(
    superuser, seeded_books, with_overlays
):
    """`x` without any selected rows surfaces a warning, doesn't push modal."""
    session = TuiSession(user=superuser, app_class=AdminTuiApp)
    async with AdminTuiApp(session=session).run_test(size=(140, 40)) as pilot:
        await pilot.pause()
        await _navigate_index_to(pilot, "Book")
        await pilot.press("x")
        await pilot.pause()
        # Should still be on the changelist.
        assert isinstance(pilot.app.screen, ChangelistScreen)


# ---------------------------------------------------------------------
# Overlay key bindings (bug 3)
# ---------------------------------------------------------------------


@pytest.mark.django_db
async def test_overlay_key_binding_fires_on_row(
    superuser, seeded_books, with_overlays
):
    """Pressing `f` on a Book row fires BookTui.mark_featured_via_tui.

    This is the bug-3 anchor: the on_key handler must look up the overlay's
    key_bindings and dispatch the named method against the focused row.
    """
    # Before: none featured.
    assert Book.objects.filter(featured=True).count() == 0

    session = TuiSession(user=superuser, app_class=AdminTuiApp)
    async with AdminTuiApp(session=session).run_test(size=(140, 40)) as pilot:
        await pilot.pause()
        await _navigate_index_to(pilot, "Book")
        # Press `f` on the first row.
        await pilot.press("f")
        await pilot.pause()

    # After: exactly one book featured.
    assert Book.objects.filter(featured=True).count() == 1


# ---------------------------------------------------------------------
# Tool screen picker
# ---------------------------------------------------------------------


@pytest.mark.django_db
async def test_g_opens_tool_screen_picker(superuser, with_overlays):
    """`g` from IndexScreen opens the tool-screen picker (library/tui.py
    registers `logs` via tui_site.register_screen)."""
    from admin_tui.screens.index import _ToolScreenPickerModal

    session = TuiSession(user=superuser, app_class=AdminTuiApp)
    async with AdminTuiApp(session=session).run_test(size=(140, 40)) as pilot:
        await pilot.pause()
        await pilot.press("g")
        await pilot.pause()
        assert isinstance(pilot.app.screen, _ToolScreenPickerModal)


# ---------------------------------------------------------------------
# Back-navigation
# ---------------------------------------------------------------------


@pytest.mark.django_db
async def test_q_pops_back_through_screen_stack(
    superuser, seeded_books, with_overlays
):
    """q pops back: changelist → index, detail → changelist."""
    session = TuiSession(user=superuser, app_class=AdminTuiApp)
    async with AdminTuiApp(session=session).run_test(size=(140, 40)) as pilot:
        await pilot.pause()
        await _navigate_index_to(pilot, "Book")
        assert isinstance(pilot.app.screen, ChangelistScreen)
        # Drill into detail.
        await pilot.press("enter")
        await pilot.pause()
        assert isinstance(pilot.app.screen, ChangeScreen)
        # Back to changelist.
        await pilot.press("q")
        await pilot.pause()
        assert isinstance(pilot.app.screen, ChangelistScreen)
        # Back to index.
        await pilot.press("q")
        await pilot.pause()
        assert isinstance(pilot.app.screen, IndexScreen)
