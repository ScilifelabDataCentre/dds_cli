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
        text-align: right;
        padding: 0;
    }
    .access {
        color: #A0FF77;
    }
    .no-access {
       background: #ff073a;
        color: #ffffff;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static(
            ACCESS_CHIP_TEXT[self.access],
            classes="no-access",  # ACCESS_CHIP_CLASSES[self.access],
            id="access-chip",
        )
