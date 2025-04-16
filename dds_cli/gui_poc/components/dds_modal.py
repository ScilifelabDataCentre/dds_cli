"""DDS Modal Screen."""

from typing import Any, Callable
from textual import events
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Label

from dds_cli.gui_poc.components.dds_button import DDSButton
from dds_cli.gui_poc.types.dds_severity_types import DDSSeverity


class DDSModalConfirmation(ModalScreen):
    """A modal screen for the GUI."""

    def __init__(
        self,
        title: str,
        message: str,
        confirm_action: Callable,
        *args: Any,
        confirm_button_text: str = "Confirm",
        confirm_severity: DDSSeverity = DDSSeverity.DEFAULT,
        **kwargs: Any,
    ):
        super().__init__(*args, **kwargs)
        self.title = title
        self.message = message
        self.confirm_button_text = confirm_button_text
        self.confirm_severity = confirm_severity
        self.confirm_action = confirm_action

    DEFAULT_CSS = """
    DDSModalConfirmation {
        align: center middle;
    }
    """

    def compose(self) -> ComposeResult:
        yield DDSModalContent(
            self.title, self.message, self.confirm_button_text, self.confirm_severity
        )

    def on_button_pressed(self, event: events.Click) -> None:
        """Handle button presses."""
        if event.button.id == "cancel":
            self.dismiss()
        elif event.button.id == "confirm":
            self.confirm_action()
            self.dismiss()


class DDSModalContent(VerticalScroll):
    """A modal content widget."""

    def __init__(
        self,
        title: str,
        message: str,
        confirm_button_text: str,
        confirm_severity: DDSSeverity,
        *args: Any,
        **kwargs: Any,
    ):
        super().__init__(*args, **kwargs)
        self.title = title
        self.message = message
        self.confirm_button_text = confirm_button_text
        self.confirm_severity = confirm_severity

    DEFAULT_CSS = """
    DDSModalContent {
        align: center middle;
        background: $surface;
        width: 80;
        height: 20;
    }   
    #dds-modal-content {
        align: center middle;
    }
    #dds-modal-title {
        width: 100%;
        text-align: center;
        background: $panel;
        dock: top;
    }
    #dds-modal-message {
        width: 100%;
        text-align: center;
    }
    #dds-modal-button-container {
        height: auto;
        align: center middle;
    }

    #dds-modal-button-container > * {
        margin: 2;
    }
    """

    def compose(self) -> ComposeResult:
        yield Label(self.title, id="dds-modal-title")
        with Vertical(id="dds-modal-content"):
            yield Label(self.message, id="dds-modal-message")
            with Horizontal(id="dds-modal-button-container"):
                yield DDSButton("Cancel", id="cancel", variant="primary")
                yield DDSButton(
                    self.confirm_button_text, id="confirm", variant=self.confirm_severity.value
                )
