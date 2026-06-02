"""Surface-freezing test: `dj_admin_tui.__all__` matches `_PUBLIC_NAMES` exactly.

This is the public-API gate at the code level. If a refactor
adds a name to `admin_tui` (or removes one) without the
justification/test/docs paper trail, this test fires.
"""

from __future__ import annotations

import importlib

import dj_admin_tui
from dj_admin_tui._internal.public_api import _PUBLIC_NAMES


def test_dunder_all_matches_public_names():
    assert set(dj_admin_tui.__all__) == set(_PUBLIC_NAMES)


def test_public_names_are_exactly_the_five_documented():
    # If this fails the constitution / spec needs updating too.
    assert set(_PUBLIC_NAMES) == {
        "register",
        "TuiAdmin",
        "tui_site",
        "field_widgets",
        "AdminTuiApp",
    }


def test_every_public_name_resolves_to_importable_object():
    for name in _PUBLIC_NAMES:
        obj = getattr(dj_admin_tui, name)
        assert obj is not None, f"dj_admin_tui.{name} resolved to None"


def test_reimport_preserves_invariant():
    # Reloading must keep the surface frozen.
    importlib.reload(dj_admin_tui)
    assert set(dj_admin_tui.__all__) == set(_PUBLIC_NAMES)
