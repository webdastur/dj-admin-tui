"""Unit tests for THEME_NAME settings validation + precedence (US4 / FR-015..018)."""

from __future__ import annotations

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings

from admin_tui import conf
from admin_tui.themes import DEFAULT_THEME_NAME, resolve_theme_name, valid_theme_names


def test_theme_name_defaults_to_none_then_django_dark():
    with override_settings(ADMIN_TUI={}):
        loaded = conf._load()
    assert loaded["THEME_NAME"] is None
    # No appearance config → the bundled django-dark theme is the resolved default.
    assert DEFAULT_THEME_NAME == "django-dark"


def test_registered_theme_name_validates():
    with override_settings(ADMIN_TUI={"THEME_NAME": "django"}):
        loaded = conf._load()
    assert loaded["THEME_NAME"] == "django"

    with override_settings(ADMIN_TUI={"THEME_NAME": "textual-dark"}):
        loaded = conf._load()
    assert loaded["THEME_NAME"] == "textual-dark"


def test_unknown_theme_name_raises_improperly_configured():
    with override_settings(ADMIN_TUI={"THEME_NAME": "no-such-theme"}):
        with pytest.raises(ImproperlyConfigured) as exc:
            conf._load()
    assert "THEME_NAME" in str(exc.value)


def test_theme_name_must_be_str():
    with override_settings(ADMIN_TUI={"THEME_NAME": 123}):
        with pytest.raises(ImproperlyConfigured):
            conf._load()


def test_django_is_a_valid_name():
    assert "django" in valid_theme_names()
    assert "django-dark" in valid_theme_names()
    assert "textual-dark" in valid_theme_names()


def test_resolve_theme_name_uses_session_then_default():
    class _S:
        theme_name = "textual-dark"

    assert resolve_theme_name(_S()) == "textual-dark"

    class _Default:
        theme_name = None

    assert resolve_theme_name(_Default()) == "django-dark"


def teardown_function(_):
    # Restore the module's frozen defaults so later tests see a clean loader.
    conf._load()
