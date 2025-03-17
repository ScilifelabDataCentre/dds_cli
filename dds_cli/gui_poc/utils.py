from textual import events
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widget import Widget
from textual.widgets import Button, Footer, Header, Label, Placeholder, Static
from textual.screen import ModalScreen

class DDSModalHeader(Widget):
    def __init__(self):
        super().__init__()

    def compose(self) -> ComposeResult:
        yield Label("DDS Modal", id="dds-modal-header")

class DDSModal(ModalScreen):
    def __init__(self, child: Widget):
        super().__init__()
        self.child = child  

    BINDINGS = [
        Binding("c", "close", "Close")
    ]

    def compose(self) -> ComposeResult:
        yield Vertical(
            DDSModalHeader(),
            VerticalScroll(
                self.child,
                id="dds-modal-content"
            ),
            Footer(),
            id="dds-modal"
        ) 

    def action_close(self) -> None:
        self.dismiss()

    def on_button_pressed(self, event: events.Click) -> None:
        if event.button.id == "close-button":
            self.dismiss()

