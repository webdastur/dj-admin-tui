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
from textual.containers import Vertical, VerticalScroll
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Select,
    Static,
    Switch,
    TextArea,
)

from admin_tui.core.audit import _change_message, _log_addition, _log_change
from admin_tui.core.forms import (
    _build_form,
    _iter_bound_fields,
    _readonly_field_names,
)
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
        Binding("escape", "back", "Cancel", show=False),
    ]

    DEFAULT_CSS = """
    ChangeScreen #detail-body {
        height: 1fr;
        padding: 1 2;
    }
    ChangeScreen .field-row {
        height: auto;
        padding: 0 0 1 0;
    }
    ChangeScreen .field-label {
        color: $text-muted;
    }
    ChangeScreen .field-error {
        color: $error;
        text-style: italic;
    }
    ChangeScreen .non-field-error {
        background: $error 20%;
        color: $error;
        padding: 0 1;
        margin-bottom: 1;
    }
    ChangeScreen .fieldset {
        margin-bottom: 1;
    }
    ChangeScreen Button {
        margin-right: 1;
    }
    """

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
        with VerticalScroll(id="detail-body"):
            yield Static(self._heading(), id="detail-heading")
            yield Static("", id="non-field-errors", classes="non-field-error")
            yield from self._compose_body()
            if self.mode in ("add", "edit"):
                with Vertical(id="form-buttons"):
                    yield Button("Save", id="save-button", variant="primary")
                    yield Button("Cancel", id="cancel-button")
        yield Footer()

    def on_mount(self) -> None:
        self._refresh_non_field_errors()

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
        with Vertical(classes="field-row"):
            yield Static(f"[dim]{bound.label}:[/]", classes="field-label")
            if name in self._readonly:
                # Render the current value as plain text — no widget.
                yield Static(self._readonly_display(bound), classes="readonly")
            else:
                factory = field_widgets.resolve(bound, self.overlay)
                widget = factory(bound)
                widget.id = f"field-{name}"
                self._widgets[name] = widget
                yield widget
            yield Static("", id=f"err-{name}", classes="field-error")

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
            return f"[b]Add {verbose}[/]"
        if self.mode == "edit":
            return f"[b]Edit {verbose}[/]: {self.obj}"
        return f"[b]{verbose}[/]: {self.obj}"

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
        if event.button.id == "save-button":
            self.action_save()
        elif event.button.id == "cancel-button":
            self.action_back()

    def action_save(self) -> None:
        if self.mode == "view":
            return
        if self.mode == "add" and not self.overlay.has_add_permission(self.request):
            return
        if self.mode == "edit" and not self.overlay.has_change_permission(
            self.request, self.obj
        ):
            return

        data = self._gather_data()
        # Re-bind the form with the gathered data so `is_valid()` runs.
        bound_form = _build_form(
            self.overlay.model_admin, self.request, obj=self.obj, data=data
        )
        if not bound_form.is_valid():
            self.form = bound_form
            self._render_errors()
            return

        is_add = self.mode == "add"
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
        self.app.pop_screen()

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
            else:
                err_static.update("")

    def _refresh_non_field_errors(self) -> None:
        if self.form is None:
            return
        non_field = self.form.non_field_errors() if self.form.is_bound else []
        target = self.query_one("#non-field-errors", Static)
        if non_field:
            target.update(" · ".join(non_field))
            target.display = True
        else:
            target.update("")
            target.display = False


# -- value extraction --------------------------------------------------


def _read_widget_value(widget: Widget) -> Any:
    """Pull the user-entered value out of a Textual widget.

    Handles the four default-widget types: Input, Switch, Select, TextArea.
    Returns a string (or list of strings for multi-value widgets) suitable
    for Django form data — `form.is_valid()` will coerce it via the field's
    `to_python`.
    """
    if isinstance(widget, TextArea):
        return widget.text
    if isinstance(widget, Switch):
        return "True" if widget.value else "False"
    if isinstance(widget, Select):
        # Select.BLANK sentinel renders as missing in form POST.
        v = widget.value
        if v is Select.BLANK or v is None:
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
