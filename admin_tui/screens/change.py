"""ChangeScreen — single-object detail / create / edit view.

Three modes:
  - `view`  : read-only fieldsets as `name: value` text (US1).
  - `add`   : empty form bound to the model; widget per field; submit
              saves a new instance.
  - `edit`  : form bound to the existing instance; widget per field;
              submit updates.

In `add` / `edit` the form comes from `model_admin.get_form(...)` so
every `clean_*` validator and the form's `clean()` method run unchanged
(Constitution I). On a successful save we call `save_model`,
`save_related`, `construct_change_message`, and `log_addition` /
`log_change` — the same sequence the web admin's _changeform_view runs.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING, Any, Literal

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Select,
    SelectionList,
    Static,
    Switch,
    TextArea,
)

from admin_tui.core.audit import _change_message, _log_addition, _log_change
from admin_tui.core.forms import (
    _build_form,
    _inline_instances,
    _iter_bound_fields,
    _readonly_field_names,
)
from admin_tui.core.request import build_request
from admin_tui.screens.action_confirm import DELETE_SENTINEL, ActionConfirmScreen
from admin_tui.widgets.registry import field_widgets

if TYPE_CHECKING:
    from django.forms import BoundField, ModelForm
    from django.http import HttpRequest

    from admin_tui._internal.session import TuiSession
    from admin_tui.options import TuiAdmin


Mode = Literal["view", "add", "edit"]


class ChangeScreen(Screen):
    """Detail / create / edit Screen. Mode set at construction."""

    BINDINGS = [
        Binding("q", "back", "Back", show=True),
        Binding("e", "edit", "Edit", show=True),
        Binding("ctrl+s", "save", "Save", show=True),
        Binding("d", "delete", "Delete", show=False),
        Binding("escape", "back", "Cancel", show=False),
    ]

    # All styling lives in the shared design system (admin_tui/styles.tcss).

    def __init__(
        self,
        *,
        session: "TuiSession",
        overlay: "TuiAdmin",
        request: "HttpRequest",
        obj: Any | None = None,
        mode: Mode = "view",
    ) -> None:
        super().__init__()
        self.session = session
        self.overlay = overlay
        self.request = request
        self.obj = obj
        # Auto-correct: `add` is obj=None, `edit`/`view` are obj=instance.
        if mode == "add" and obj is not None:
            mode = "edit"
        if mode != "view" and obj is None and mode == "edit":
            mode = "add"
        self.mode: Mode = mode
        self.form: "ModelForm | None" = None
        self._widgets: dict[str, Widget] = {}
        self._readonly: set[str] = set()

    # ---- mount ---------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield Static(self._breadcrumb(), id="change-breadcrumb", classes="atui-breadcrumb")
        with VerticalScroll(id="detail-body"):
            yield Static(self._heading(), id="detail-heading")
            if self.mode in ("add", "edit"):
                # Only the editable modes have a (hidden-until-populated) error
                # banner — view mode must never show an empty error bar.
                errors = Static("", id="non-field-errors", classes="non-field-error")
                errors.display = False
                yield errors
            yield from self._compose_body()
            if self.mode in ("add", "edit"):
                with Horizontal(id="form-buttons"):
                    yield Button("Save", id="save-button",
                                 classes="atui-btn atui-btn-primary")
                    yield Button("Save and add another", id="save-add-button",
                                 classes="atui-btn atui-btn-primary")
                    yield Button("Save and continue editing", id="save-continue-button",
                                 classes="atui-btn atui-btn-primary")
                    yield Button("Cancel", id="cancel-button",
                                 classes="atui-btn atui-btn-default")
                    if self.mode == "edit" and self.overlay.has_delete_permission(
                        self.request, self.obj
                    ):
                        yield Static(id="submit-spacer", classes="atui-spacer")
                        yield Button("Delete", id="delete-button",
                                     classes="atui-btn atui-btn-danger")
        yield Footer()

    def on_mount(self) -> None:
        self._refresh_non_field_errors()

    def _breadcrumb(self) -> str:
        meta = self.overlay.model_admin.model._meta
        app_label = meta.app_config.verbose_name if meta.app_config else meta.app_label
        tail = "Add" if self.mode == "add" else (str(self.obj) if self.obj else "")
        crumb = f"Home › {app_label} › {meta.verbose_name_plural}"
        return f"{crumb} › {tail}" if tail else crumb

    # ---- compose helpers ----------------------------------------------

    def _compose_body(self) -> Iterable[Widget]:
        if self.mode == "view":
            yield from self._compose_view_body()
        else:
            # Build the form once and stash it.
            self.form = _build_form(
                self.overlay.model_admin, self.request, obj=self.obj
            )
            self._readonly = _readonly_field_names(
                self.overlay.model_admin, self.request, self.obj
            )
            yield from self._compose_form_body()

    def _compose_view_body(self) -> Iterable[Widget]:
        for set_name, set_body in self._fieldsets():
            with Vertical(classes="fieldset"):
                if set_name:
                    yield Static(f"[b]{set_name}[/]", classes="fieldset-name")
                for field_name in set_body.get("fields", []):
                    yield Static(self._format_field_value(field_name),
                                 classes="field-row")
        # R15: inline relations rendered as read-only sections below the
        # main fieldsets. Editable inline rows are deferred to a follow-up.
        if self.obj is not None:
            yield from self._compose_inlines()

    def _compose_inlines(self) -> Iterable[Widget]:
        inlines = _inline_instances(
            self.overlay.model_admin, self.request, self.obj
        )
        for inline in inlines:
            verbose = inline.model._meta.verbose_name_plural
            with Vertical(classes="fieldset inline-section"):
                yield Static(
                    f"[b]{verbose}[/]  [dim](read-only in v1)[/]",
                    classes="fieldset-name",
                )
                related = self._related_queryset(inline)
                count = related.count()
                if count == 0:
                    yield Static("[dim](none)[/]", classes="field-row")
                else:
                    fields = list(getattr(inline, "fields", None) or [])
                    if not fields:
                        # Fall back to model fields if inline didn't declare any.
                        fields = [
                            f.name for f in inline.model._meta.fields
                            if f.name not in {"id", "book"}
                        ]
                    for related_obj in related:
                        bits = []
                        for f in fields:
                            value = getattr(related_obj, f, "")
                            bits.append(f"{f}={value!s}")
                        yield Static(
                            "• " + ", ".join(bits),
                            classes="field-row",
                        )

    def _related_queryset(self, inline) -> Any:  # type: ignore[no-untyped-def]
        """The queryset of related rows for this inline + this object."""
        fk_name = inline.fk_name or _detect_fk_to(
            inline.model, type(self.obj)
        )
        if fk_name is None:
            return inline.model._default_manager.none()
        return inline.model._default_manager.filter(
            **{fk_name: self.obj.pk}
        )

    def _compose_form_body(self) -> Iterable[Widget]:
        assert self.form is not None
        rendered: set[str] = set()
        for set_name, set_body in self._fieldsets():
            with Vertical(classes="fieldset"):
                if set_name:
                    yield Static(f"[b]{set_name}[/]", classes="fieldset-name")
                for field_name in set_body.get("fields", []):
                    if isinstance(field_name, (list, tuple)):
                        # Grouped fields — render flat.
                        for sub in field_name:
                            yield from self._compose_field(sub)
                            rendered.add(sub)
                    else:
                        yield from self._compose_field(field_name)
                        rendered.add(field_name)
        # Any form fields not in fieldsets (e.g. when overlay/admin
        # doesn't declare any) — render in the natural form order.
        for name, _bound in _iter_bound_fields(self.form):
            if name not in rendered:
                yield from self._compose_field(name)

    def _compose_field(self, name: str) -> Iterable[Widget]:
        assert self.form is not None
        if name not in self.form.fields:
            # Fieldsets can name properties or methods that aren't form
            # fields — render them read-only as in view mode.
            yield Static(self._format_field_value(name), classes="field-row")
            return
        bound = self.form[name]
        # Django layout: label on the left, the widget (+ inline error) on the
        # right.
        with Horizontal(classes="field-row"):
            yield Static(f"{bound.label}:", classes="field-label")
            with Vertical(classes="field-widget"):
                if name in self._readonly:
                    # Render the current value as plain text — no widget.
                    yield Static(self._readonly_display(bound), classes="readonly")
                else:
                    # Building a widget can hit the DB (FK/M2M option queries).
                    # On failure, render read-only rather than crash the form.
                    try:
                        factory = field_widgets.resolve(bound, self.overlay)
                        widget = factory(bound)
                        widget.id = f"field-{name}"
                        self._widgets[name] = widget
                        yield widget
                    except Exception as exc:  # noqa: BLE001
                        yield Static(
                            f"[i](unavailable: {type(exc).__name__})[/]",
                            classes="readonly",
                        )
                # Hidden until there's an error, so fields stack tightly
                # (an always-present empty line under each field reads as a
                # big gap — the web admin only shows the error when present).
                err = Static("", id=f"err-{name}", classes="field-error")
                err.display = False
                yield err

    def _readonly_display(self, bound: "BoundField") -> str:
        v = bound.value()
        return "—" if v is None else str(v)

    # ---- view-mode helpers --------------------------------------------

    def _fieldsets(self) -> list[tuple[str | None, dict[str, Any]]]:
        if self.overlay.detail_fieldsets is not None:
            raw = self.overlay.detail_fieldsets
        else:
            raw = self.overlay.model_admin.get_fieldsets(self.request, self.obj)
        out: list[tuple[str | None, dict[str, Any]]] = []
        for name, body in raw:
            out.append((name, body if isinstance(body, dict) else {"fields": list(body)}))
        return out

    def _heading(self) -> str:
        verbose = self.overlay.model_admin.model._meta.verbose_name
        if self.mode == "add":
            return f"Add {verbose}"
        if self.mode == "edit":
            return f"Change {verbose}: {self.obj}"
        return f"{verbose}: {self.obj}"

    def _format_field_value(self, field_name: Any) -> str:
        if isinstance(field_name, (list, tuple)):
            return " · ".join(self._format_field_value(f) for f in field_name)
        if self.obj is None:
            return f"[dim]{field_name}:[/] —"
        value = getattr(self.obj, field_name, None)
        display = "—" if value is None else str(value)
        return f"[dim]{field_name}:[/] {display}"

    # ---- save flow -----------------------------------------------------

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id
        if bid == "save-button":
            self.action_save()
        elif bid == "save-add-button":
            self.action_save_add_another()
        elif bid == "save-continue-button":
            self.action_save_continue()
        elif bid == "delete-button":
            self.action_delete()
        elif bid == "cancel-button":
            self.action_back()

    def _do_save(self) -> Any | None:
        """Validate + persist. Returns the saved object, or None if the form was
        invalid or the save errored (in which case the operator stays here)."""
        if self.mode == "view":
            return None
        if self.mode == "add" and not self.overlay.has_add_permission(self.request):
            return None
        if self.mode == "edit" and not self.overlay.has_change_permission(
            self.request, self.obj
        ):
            return None

        data = self._gather_data()
        # Re-bind the form with the gathered data so `is_valid()` runs.
        bound_form = _build_form(
            self.overlay.model_admin, self.request, obj=self.obj, data=data
        )
        if not bound_form.is_valid():
            self.form = bound_form
            self._render_errors()
            return None

        is_add = self.mode == "add"
        # The save itself can fail at the DB layer (constraints, missing table,
        # …). Surface it as a notification and stay on the form — never crash.
        try:
            new_obj = bound_form.save(commit=False)
            self.overlay.before_save(self.request, new_obj, created=is_add)
            # Mirror django.contrib.admin's _changeform_view sequence:
            self.overlay.model_admin.save_model(
                self.request, new_obj, bound_form, change=not is_add
            )
            self.overlay.model_admin.save_related(
                self.request, bound_form, [], change=not is_add
            )

            change_message = _change_message(
                self.overlay.model_admin, self.request, bound_form, [], add=is_add
            )
            if is_add:
                _log_addition(
                    self.overlay.model_admin, self.request, new_obj, change_message
                )
            else:
                _log_change(
                    self.overlay.model_admin, self.request, new_obj, change_message
                )

            self.overlay.after_save(self.request, new_obj, created=is_add)
        except Exception as exc:  # noqa: BLE001 — last-resort UI guard
            self.app.notify(
                f"Save failed: {type(exc).__name__}: {exc}",
                title="Error",
                severity="error",
                timeout=10,
            )
            return None
        return new_obj

    def action_save(self) -> None:
        if self._do_save() is not None:
            self.app.pop_screen()

    def action_save_add_another(self) -> None:
        if self._do_save() is None:
            return
        self.app.pop_screen()
        req = build_request(self.session.user)
        req._tui_session = self.session
        screen_cls = self.app.screen_for_detail(self.overlay, req, None)
        self.app.push_screen(
            screen_cls(
                session=self.session, overlay=self.overlay, request=req,
                obj=None, mode="add",
            )
        )

    def action_save_continue(self) -> None:
        saved = self._do_save()
        if saved is None:
            return
        self.app.pop_screen()
        req = build_request(self.session.user)
        req._tui_session = self.session
        try:
            obj = self.overlay.model_admin.get_queryset(req).get(pk=saved.pk)
        except Exception:  # noqa: BLE001
            return
        screen_cls = self.app.screen_for_detail(self.overlay, req, obj)
        self.app.push_screen(
            screen_cls(
                session=self.session, overlay=self.overlay, request=req,
                obj=obj, mode="edit",
            )
        )

    def action_delete(self) -> None:
        if self.mode != "edit" or self.obj is None:
            return
        if not self.overlay.has_delete_permission(self.request, self.obj):
            return
        req = build_request(self.session.user)
        req._tui_session = self.session
        queryset = self.overlay.model_admin.get_queryset(req).filter(pk=self.obj.pk)
        self.app.push_screen(
            ActionConfirmScreen(
                session=self.session,
                overlay=self.overlay,
                request=req,
                action_name=DELETE_SENTINEL,
                action_label="Delete",
                queryset=queryset,
                kind="delete",
            )
        )

    def action_edit(self) -> None:
        if self.mode != "view":
            return
        if not self.overlay.has_change_permission(self.request, self.obj):
            return
        self.app.pop_screen()
        screen_cls = self.app.screen_for_detail(
            self.overlay, self.request, self.obj
        )
        self.app.push_screen(
            screen_cls(
                session=self.session,
                overlay=self.overlay,
                request=self.request,
                obj=self.obj,
                mode="edit",
            )
        )

    def action_back(self) -> None:
        self.app.pop_screen()

    def on_screen_resume(self) -> None:
        """After a delete confirmation pops back here, if the object is gone,
        return to the changelist instead of showing a stale detail."""
        if self.mode == "edit" and self.obj is not None:
            try:
                exists = (
                    self.overlay.model_admin.get_queryset(self.request)
                    .filter(pk=self.obj.pk)
                    .exists()
                )
            except Exception:  # noqa: BLE001
                exists = True
            if not exists:
                self.app.pop_screen()

    # ---- data gathering + error rendering -----------------------------

    def _gather_data(self) -> dict[str, Any]:
        assert self.form is not None
        out: dict[str, Any] = {}
        for name, _bound in _iter_bound_fields(self.form):
            if name in self._readonly:
                continue
            widget = self._widgets.get(name)
            if widget is None:
                continue
            out[name] = _read_widget_value(widget)
        return out

    def _render_errors(self) -> None:
        assert self.form is not None
        self._refresh_non_field_errors()
        for name, _bound in _iter_bound_fields(self.form):
            err_static = self.query_one(f"#err-{name}", Static)
            errors = self.form.errors.get(name)
            if errors:
                err_static.update(" · ".join(errors))
                err_static.display = True
            else:
                err_static.update("")
                err_static.display = False

    def _refresh_non_field_errors(self) -> None:
        if self.form is None:
            return
        try:
            target = self.query_one("#non-field-errors", Static)
        except Exception:
            return  # view mode has no error banner
        non_field = self.form.non_field_errors() if self.form.is_bound else []
        if non_field:
            target.update(" · ".join(non_field))
            target.display = True
        else:
            target.update("")
            target.display = False


# -- value extraction --------------------------------------------------


def _detect_fk_to(inline_model, parent_model) -> str | None:  # type: ignore[no-untyped-def]
    """Find the field on `inline_model` that FK-points at `parent_model`."""
    from django.db.models import ForeignKey

    for field in inline_model._meta.get_fields():
        if isinstance(field, ForeignKey) and field.related_model is parent_model:
            return field.name
    return None


def _read_widget_value(widget: Widget) -> Any:
    """Pull the user-entered value out of a Textual widget.

    Handles the default-widget types: Input, Switch, Select, SelectionList,
    TextArea. Returns a string (or a list of strings for multi-value widgets
    like M2M) suitable for Django form data — `form.is_valid()` will coerce it
    via the field's `to_python`. A plain dict carrying a list value is read
    back correctly by Django's `SelectMultiple.value_from_datadict` (it falls
    back to `data.get`, which returns the list as-is).
    """
    if isinstance(widget, SelectionList):
        # Multi-value (M2M): list of selected pks as strings.
        return [str(v) for v in widget.selected]
    if isinstance(widget, TextArea):
        return widget.text
    if isinstance(widget, Switch):
        return "True" if widget.value else "False"
    if isinstance(widget, Select):
        # Both no-selection sentinels (BLANK / NULL) render as missing in POST.
        v = widget.value
        if v is None or v is Select.BLANK or v is Select.NULL:
            return ""
        return str(v)
    if isinstance(widget, Input):
        return widget.value
    # Fallback for user-defined widgets — duck-type on .value / .text.
    if hasattr(widget, "value"):
        v = widget.value
        return "" if v is None else str(v)
    if hasattr(widget, "text"):
        return widget.text
    return ""
