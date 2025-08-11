"""Message of the day card"""

from textual.app import ComposeResult
from textual.widgets import Static
from textual.widget import Widget


class MOTDCard(Widget):
    """Message of the day card"""

    def __init__(self, title: str, message: str):
        super().__init__()
        self.title = title
        self.message = message

    DEFAULT_CSS = """
    MOTDCard {
        background: #5C4D00;
        border: tall #FFE666;
        color: $text;
        height: auto;
        padding: 0 1;
    }

    .title {
        text-style: bold;
    }

    MOTDCard.-hover {
        background: #776500;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static(self.title, classes="title")
        yield Static(self.message)

    def on_enter(self) -> None:
        """Handle mouse enter event for hover effect."""
        self.add_class("-hover")

    def on_leave(self) -> None:
        """Handle mouse leave event for hover effect."""
        self.remove_class("-hover")
