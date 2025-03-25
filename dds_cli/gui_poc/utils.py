"""Utility widgets."""

from textual import events
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical, VerticalScroll
from textual.widget import Widget
from textual.widgets import Button, Footer, Label, Markdown
from textual.screen import ModalScreen


class DDSModalHeader(Widget):
    """DDS modal header widget."""

    def __init__(self, title: str):
        super().__init__()
        self.title = title

    def compose(self) -> ComposeResult:
        yield Label(self.title, id="dds-modal-header")


class DDSModal(ModalScreen):
    """DDS modal widget."""

    def __init__(self, child: Widget, title: str = "DDS Modal"):
        super().__init__()
        self.child = child
        self.title = title

    # Binding for closing the modal
    BINDINGS = [Binding("c", "close", "Close")]

    def compose(self) -> ComposeResult:
        yield Vertical(
            DDSModalHeader(self.title),
            VerticalScroll(self.child, id="dds-modal-content"),
            Footer(),
            id="dds-modal",
        )

    def action_close(self) -> None:
        """Action to close the modal."""
        self.dismiss()

    def on_button_pressed(self, event: events.Click) -> None:
        """Handles button presses."""
        if event.button.id == "close-button":
            self.dismiss()


class DDSSidebar(Widget):
    """DDS sidebar widget."""

    def __init__(self, items: list[str], help_text: str = "Help", title: str = "DDS Sidebar"):
        super().__init__()
        self.items = items
        self.help_text = help_text
        self.title = title

    def compose(self) -> ComposeResult:
        with Container(id="dds-sidebar"):
            with Vertical(id="dds-sidebar-items"):
                for item in self.items:
                    yield Button(item.capitalize(), id=item, variant="primary")
            with Vertical(id="dds-sidebar-help"):
                yield Button("Help", id="help", variant="primary")

    def on_mount(self) -> None:
        """On mount, set the border title of the sidebar."""
        self.query_one(Container).border_title = self.title

    def on_button_pressed(self, event: events.Click) -> None:
        """Handles button presses."""
        if event.button.id == "help":
            self.app.push_screen(DDSModal(Markdown(self.help_text), title="Help"))
