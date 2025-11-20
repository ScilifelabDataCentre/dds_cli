"""DDS Access Chip"""

from typing import Any
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static

ACCESS_CHIP_CLASSES = {
    True: "access",
    False: "no-access",
}

ACCESS_CHIP_TEXT = {
    True: "Access Granted",
    False: "Access Denied",
}


class AccessChip(Widget):
    """A widget for the access of the project."""

    def __init__(self, access: bool, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.access = access

    DEFAULT_CSS = """
    #access-chip {
        height: auto;
        width: auto;
        padding: 0 1;
        text-align: center;
        text-style: bold;
    }
    .access {
        color: #ebf7e6;
        background: #41911f;
    }
    .no-access {
        background: #ff073a;
        color: #fae1e6;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static(
            ACCESS_CHIP_TEXT[self.access],
            classes=ACCESS_CHIP_CLASSES[self.access],
            id="access-chip",
        )
