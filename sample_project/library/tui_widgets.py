"""Custom Textual widget for ColorField (US4 / FR-025 demonstration).

Pure Textual primitives: a swatch (Static) + an Input bound to the hex
value. Constitution VI in practice — admin_tui does not introduce a
parallel widget class; downstream code subclasses textual.widget.Widget
directly.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Input, Static


class ColorPickerWidget(Widget):
    """A horizontal color swatch + hex Input."""

    DEFAULT_CSS = """
    ColorPickerWidget {
        layout: horizontal;
        height: 3;
        width: 1fr;
    }
    ColorPickerWidget > .swatch {
        width: 6;
        height: 3;
        content-align: center middle;
    }
    ColorPickerWidget > Input {
        width: 1fr;
        height: 3;
    }
    """

    def __init__(self, value: str | None = "#000000") -> None:
        super().__init__()
        self._initial_value = value or "#000000"

    def compose(self) -> ComposeResult:
        yield Static("    ", classes="swatch")
        yield Input(value=self._initial_value, id="color-hex-input")

    def on_mount(self) -> None:
        self._update_swatch(self._initial_value)

    @property
    def value(self) -> str:
        try:
            return self.query_one("#color-hex-input", Input).value
        except Exception:
            return self._initial_value

    def on_input_changed(self, event: Input.Changed) -> None:
        self._update_swatch(event.value)

    def _update_swatch(self, color: str) -> None:
        try:
            swatch = self.query_one(".swatch", Static)
        except Exception:
            return
        # Only apply if it looks like a valid hex; otherwise leave the
        # previous color so the swatch doesn't strobe while typing.
        if len(color) == 7 and color.startswith("#") and all(
            c in "0123456789abcdefABCDEF" for c in color[1:]
        ):
            swatch.styles.background = color
