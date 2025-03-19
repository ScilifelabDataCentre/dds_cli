from textual import events
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widget import Widget
from textual.widgets import Button, Footer, Header, Label, Placeholder, Static
from textual.screen import ModalScreen

class DDSModalHeader(Widget):
    def __init__(self, title: str):
        super().__init__()
        self.title = title

    def compose(self) -> ComposeResult:
        yield Label(self.title, id="dds-modal-header")

class DDSModal(ModalScreen):
    def __init__(self, child: Widget, title: str = "DDS Modal"):
        super().__init__()
        self.child = child  
        self.title = title

    BINDINGS = [
        Binding("c", "close", "Close")
    ]

    def compose(self) -> ComposeResult:
        yield Vertical(
            DDSModalHeader(self.title),
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