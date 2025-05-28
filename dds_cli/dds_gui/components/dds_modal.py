"""DDS Modal Widgets."""

from typing import Any, Callable
from textual import events
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Label

from dds_cli.dds_gui.components.dds_button import DDSButton
from dds_cli.dds_gui.components.dds_footer import DDSFooter
from dds_cli.dds_gui.types.dds_severity_types import DDSSeverity


class DDSModal(ModalScreen):
    """A modal screen for the GUI.
    Args:
        title: The title of the modal, displayed in the header.
        content: The content of the modal.
    """

    def __init__(self, title: str, content: Widget, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.title = title
        self.content = content

    ## Bindings for the modal, close the modal on escape key
    BINDINGS = [Binding("escape", "dismiss", "Close")]

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
        """Close the modal. To be called by the content widget."""
        self.dismiss()


class DDSModalConfirmation(DDSModal):
    """A modal screen for the GUI.
    Args:
        title: The title of the modal, displayed in the header.
        message: The message of the modal confirmation, displayed in the content.
        confirm_action: The action to be called when the confirm button is pressed.
        confirm_button_text: The text of the confirm button, defaults to "Confirm".
        confirm_severity: The severity of the confirm button, defaults to DEFAULT.
    """

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
        super().__init__(
            title,
            self.create_content(message, confirm_button_text, confirm_severity),
            *args,
            **kwargs,
        )
        self.confirm_action = confirm_action

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

    def create_content(
        self, message: str, confirm_button_text: str, confirm_severity: DDSSeverity
    ) -> Widget:
        """Create the content of the modal."""
        return Vertical(
            Label(message, id="dds-modal-message"),
            Horizontal(
                DDSButton("Cancel", id="cancel", variant="primary"),
                DDSButton(confirm_button_text, id="confirm", variant=confirm_severity.value),
                id="dds-modal-button-container",
            ),
            id="dds-modal-content",
        )

    def on_button_pressed(self, event: events.Click) -> None:
        """Handle button presses."""
        if event.button.id == "cancel":
            self.close_modal()
        elif event.button.id == "confirm":
            self.confirm_action()
            self.close_modal()
