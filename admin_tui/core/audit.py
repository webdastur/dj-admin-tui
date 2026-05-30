"""Audit logging — pass-through to ModelAdmin's own helpers.

SC-004 requires "user, action flag, content type, and change message
match those the web admin would produce for the same inputs." The only
way to satisfy that is to call the admin's own `log_*` helpers and
`construct_change_message`. We never construct `LogEntry` rows directly.

See research.md § R7.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from django.contrib.admin import ModelAdmin
    from django.forms import ModelForm
    from django.http import HttpRequest


def _log_addition(
    model_admin: "ModelAdmin",
    request: "HttpRequest",
    obj: Any,
    change_message: Any,
) -> Any:
    return model_admin.log_addition(request, obj, change_message)


def _log_change(
    model_admin: "ModelAdmin",
    request: "HttpRequest",
    obj: Any,
    change_message: Any,
) -> Any:
    return model_admin.log_change(request, obj, change_message)


def _log_deletion(
    model_admin: "ModelAdmin",
    request: "HttpRequest",
    obj: Any,
) -> Any:
    """Log a delete. Call BEFORE actually deleting so `str(obj)` resolves."""
    return model_admin.log_deletion(request, obj, str(obj))


def _change_message(
    model_admin: "ModelAdmin",
    request: "HttpRequest",
    form: "ModelForm",
    formsets: list,
    *,
    add: bool,
) -> Any:
    """The same payload the web admin would write to LogEntry.change_message."""
    return model_admin.construct_change_message(request, form, formsets, add)
