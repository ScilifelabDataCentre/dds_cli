"""DDS Key Pair Table"""

from typing import Any
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widget import Widget
from textual.widgets import Static, Rule


class DDSKeyPairTable(Widget):
    """A widget for the key pair table."""

    def __init__(self, data: list[tuple[str, str]], *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.data = data

    DEFAULT_CSS = """
    #key-pair-table {
        width: 100%;
    }
    .key-pair-row {
        width: 100%;
        height: auto;
        border-bottom: solid $primary;
    }

    .key-pair-row:last-of-type {
        border-bottom: none;
        padding-bottom: 0;
    }
    .key-pair-row #key {
        text-style: bold;
        width: 50%;
    }
    .key-pair-row #value {
        text-align: right;
        width: 50%;
    }
    
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="key-pair-table"):
            for key, value in self.data:
                with Horizontal(classes="key-pair-row"):
                    yield Static(key, id="key")
                    yield Static(value, id="value")
