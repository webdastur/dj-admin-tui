"""Synthetic request + capturing messages backend.

The two invariants this pins:
  1. `build_request(user)` returns a real HttpRequest with `.user is user`.
  2. `request._messages` is a `_CapturingMessageStorage`, and messages
     emitted via Django's `add_message(...)` land in `request._messages.captured`.

Without (2), `ModelAdmin.message_user(...)` either drops messages silently
or raises `MessageFailure`.
"""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.messages import add_message
from django.http import HttpRequest

from dj_admin_tui.core.messages import _CapturingMessageStorage
from dj_admin_tui.core.request import build_request


def test_build_request_attaches_user(db):
    User = get_user_model()
    user = User.objects.create_user(username="alice", password="x", is_staff=True)
    request = build_request(user)
    assert isinstance(request, HttpRequest)
    assert request.user is user


def test_build_request_attaches_capturing_messages(db):
    User = get_user_model()
    user = User.objects.create_user(username="bob", password="x", is_staff=True)
    request = build_request(user)
    storage = request._messages
    assert isinstance(storage, _CapturingMessageStorage)
    assert storage.captured == []


def test_messages_framework_writes_to_captured(db):
    User = get_user_model()
    user = User.objects.create_user(username="cara", password="x", is_staff=True)
    request = build_request(user)
    add_message(request, messages.INFO, "hello")
    add_message(request, messages.WARNING, "watch out", extra_tags="audit")
    assert request._messages.captured == [
        (messages.INFO, "hello", ""),
        (messages.WARNING, "watch out", "audit"),
    ]


def test_build_request_carries_query_string(db):
    User = get_user_model()
    user = User.objects.create_user(username="dave", password="x", is_staff=True)
    request = build_request(user, query={"q": "Tolkien", "page": "2"})
    assert request.GET["q"] == "Tolkien"
    assert request.GET["page"] == "2"


def test_tui_session_marker_present(db):
    User = get_user_model()
    user = User.objects.create_user(username="eve", password="x", is_staff=True)
    request = build_request(user)
    # CLI replaces None with a real TuiSession before screens render;
    # we just pin that the attribute exists.
    assert hasattr(request, "_tui_session")
