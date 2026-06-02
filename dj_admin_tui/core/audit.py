"""Audit logging — pass-through to ModelAdmin's own helpers.

The user, action flag, content type, and change message must match what the
web admin produces for the same inputs. The only way to satisfy that is to
call the admin's own `log_*` helpers and `construct_change_message`; we never
construct `LogEntry` rows directly.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from django.contrib.admin import ModelAdmin
    from django.forms import ModelForm
    from django.http import HttpRequest


def _log_addition(
    model_admin: ModelAdmin,
    request: HttpRequest,
    obj: Any,
    change_message: Any,
) -> Any:
    return model_admin.log_addition(request, obj, change_message)


def _log_change(
    model_admin: ModelAdmin,
    request: HttpRequest,
    obj: Any,
    change_message: Any,
) -> Any:
    return model_admin.log_change(request, obj, change_message)


def _log_deletion(
    model_admin: ModelAdmin,
    request: HttpRequest,
    obj: Any,
) -> Any:
    """Log a single-object delete. Call BEFORE actual deletion.

    Django 6.0 renamed `log_deletion(obj, object_repr)` to
    `log_deletions(queryset)`. We dispatch to whichever the installed
    version exposes — the per-object signature stays the same to callers.
    """
    if hasattr(model_admin, "log_deletions"):
        # Django 6.0+
        qs = model_admin.model._default_manager.filter(pk=obj.pk)
        return model_admin.log_deletions(request, qs)
    # Django 4.2 / 5.2 — older per-object API.
    return model_admin.log_deletion(request, obj, str(obj))


def _log_deletions(
    model_admin: ModelAdmin,
    request: HttpRequest,
    queryset: Any,
) -> Any:
    """Batch deletion log — one call per queryset.

    On Django 6.0+ uses `log_deletions(queryset)` directly; on older
    Django falls back to per-object `log_deletion(...)`.
    """
    if hasattr(model_admin, "log_deletions"):
        return model_admin.log_deletions(request, queryset)
    # Django 4.2 / 5.2 — loop per object.
    for obj in queryset:
        model_admin.log_deletion(request, obj, str(obj))
    return None


def _change_message(
    model_admin: ModelAdmin,
    request: HttpRequest,
    form: ModelForm,
    formsets: list,
    *,
    add: bool,
) -> Any:
    """The same payload the web admin would write to LogEntry.change_message."""
    return model_admin.construct_change_message(request, form, formsets, add)
