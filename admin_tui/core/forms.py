"""Build the admin's ModelForm — Constitution I in code.

`ModelAdmin.get_form(request, obj, change)` is the admin's authoritative
form factory. It honors `formfield_overrides`, `radio_fields`,
`readonly_fields`, and every custom `clean_*` / `clean` method declared
on the form. We never reimplement that surface (research.md § R5).

For the TUI we receive form-shaped data from the active screen's widgets
and feed it back through the same form for validation, so `is_valid()`
and `clean()` run unchanged.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from django.contrib.admin import ModelAdmin
    from django.forms import BoundField, ModelForm
    from django.http import HttpRequest


def _build_form(
    model_admin: "ModelAdmin",
    request: "HttpRequest",
    *,
    obj: Any | None = None,
    data: dict[str, Any] | None = None,
) -> "ModelForm":
    """Instantiate the admin's ModelForm in add / edit mode.

    Args:
        model_admin: the registered ModelAdmin.
        request: the synthetic HttpRequest with `request.user` set.
        obj: existing instance for edit mode; `None` for add.
        data: form data to validate; `None` for an unbound rendering.

    Returns:
        A `ModelForm` instance — `form.is_valid()`, `form.errors`, etc. are
        the admin's exact behavior.
    """
    change = obj is not None
    FormClass = model_admin.get_form(request, obj=obj, change=change)
    return FormClass(data=data, instance=obj)


def _iter_bound_fields(form: "ModelForm") -> "list[tuple[str, BoundField]]":
    """Yield `(name, BoundField)` pairs in the form's field-declaration order."""
    return [(name, form[name]) for name in form.fields]


def _readonly_field_names(
    model_admin: "ModelAdmin",
    request: "HttpRequest",
    obj: Any | None = None,
) -> set[str]:
    """The set of fields the admin treats as read-only on this view."""
    return set(model_admin.get_readonly_fields(request, obj))


def _inline_instances(
    model_admin: "ModelAdmin",
    request: "HttpRequest",
    obj: Any | None = None,
) -> list:
    """Return the InlineModelAdmin instances for `obj`.

    Skips inlines the user lacks `has_view_permission` on — same
    permission gate the web admin's change_view applies (R15).
    """
    instances = model_admin.get_inline_instances(request, obj)
    return [
        inline
        for inline in instances
        if inline.has_view_permission(request, obj)
    ]
