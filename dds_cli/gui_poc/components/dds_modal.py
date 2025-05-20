"""DDS Modal Screen."""

from typing import Any, Callable
from textual import events
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Footer, Label

from dds_cli.gui_poc.components.dds_button import DDSButton
from dds_cli.gui_poc.components.dds_footer import DDSFooter
from dds_cli.gui_poc.types.dds_severity_types import DDSSeverity


class DDSModal(ModalScreen):
    """A modal screen for the GUI."""

    def __init__(self, title: str, content: Widget, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.title = title
        self.content = content


    BINDINGS = [
        Binding("escape", "dismiss", "Close")
    ]

    DEFAULT_CSS = """
    DDSModal {
        align: center middle;
    }
    #dds-modal-container {
        align: center middle;
        background: $surface;
        width: 80;
        height: 20;
    }   
    #dds-modal-content {
        align: center middle;
        padding: 1;
        height: 100%;
    }
    .modal-content {
        height: 100%;
        border: round $panel;
    } 

    .modal-content > * {
        height: auto;
    }
    #dds-modal-title {
        width: 100%;
        text-align: center;
        background: $panel;
        dock: top;
    }
    """

    def compose(self) -> ComposeResult:
        with Container(id="dds-modal-container"):
            yield Label(self.title, id="dds-modal-title")
            with VerticalScroll(id="dds-modal-content"):
                yield self.content
            yield DDSFooter()    

    def close_modal(self) -> None:
        """Close the modal."""
        self.dismiss()


class DDSModalConfirmation(DDSModal):
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
        super().__init__(title, DDSModalConfirmationContent(title, message, confirm_button_text, confirm_severity), *args, **kwargs)
        self.title = title
        self.message = message
        self.confirm_button_text = confirm_button_text
        self.confirm_severity = confirm_severity
        self.confirm_action = confirm_action

    def on_button_pressed(self, event: events.Click) -> None:
        """Handle button presses."""
        if event.button.id == "cancel":
            self.dismiss()
        elif event.button.id == "confirm":
            self.confirm_action()
            self.dismiss()

class DDSModalConfirmationContent(VerticalScroll):
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
        with Vertical(id="dds-modal-content"):
            yield Label(self.message, id="dds-modal-message")
            with Horizontal(id="dds-modal-button-container"):
                yield DDSButton("Cancel", id="cancel", variant="primary")
                yield DDSButton(
                    self.confirm_button_text, id="confirm", variant=self.confirm_severity.value
                )
