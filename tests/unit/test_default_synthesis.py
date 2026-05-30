"""Default TuiAdmin synthesis.

For a model with a registered ModelAdmin but no TuiAdmin overlay,
`tui_site.get_or_synthesize(model)` must return a working TuiAdmin instance
pointing at the source ModelAdmin. Repeated calls must return the SAME
instance (cache stability).
"""

from __future__ import annotations

import pytest
from django.contrib import admin as django_admin

from admin_tui import TuiAdmin, tui_site
from sample_project.library.models import Author, Book
from sample_project.plain_app.models import Note


@pytest.fixture(autouse=True)
def _reset_synth_cache():
    """Each test gets a fresh synth cache to avoid order-dependence."""
    tui_site._synth_cache.clear()
    tui_site._registry.clear()
    yield
    tui_site._synth_cache.clear()
    tui_site._registry.clear()


def test_zero_config_model_is_synthesised():
    overlay = tui_site.get_or_synthesize(Note)
    assert isinstance(overlay, TuiAdmin)
    # The synthesised overlay must point at the registered ModelAdmin.
    assert overlay.model_admin is django_admin.site._registry[Note]


def test_synth_returns_cached_instance():
    first = tui_site.get_or_synthesize(Book)
    second = tui_site.get_or_synthesize(Book)
    assert first is second


def test_synth_does_not_leak_across_models():
    a = tui_site.get_or_synthesize(Book)
    b = tui_site.get_or_synthesize(Author)
    assert a is not b
    assert a.model_admin is not b.model_admin


def test_explicit_registration_beats_synthesis():
    class CustomBookTui(TuiAdmin):
        row_actions = ["custom"]

    tui_site.register(Book, CustomBookTui)
    overlay = tui_site.get_or_synthesize(Book)
    assert isinstance(overlay, CustomBookTui)
    assert overlay.row_actions == ["custom"]
