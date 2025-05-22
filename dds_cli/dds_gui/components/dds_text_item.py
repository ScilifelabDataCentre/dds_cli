"""DDS Text Item"""

from typing import Any
from textual.app import ComposeResult
from textual.widgets import Static


class DDSTextItem(Static):
    """A container widget for a text item."""
    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)

    DEFAULT_CSS = """
    DDSTextItem {
        padding: 0 0;
    }
    """


class DDSTextTitle(DDSTextItem):
    """A container widget for a text title."""
    DEFAULT_CSS = """
    DDSTextTitle {
        text-style: bold underline;
    }
    """


class DDSTextSubtitle(DDSTextItem):
    """A container widget for a text subtitle."""
    DEFAULT_CSS = """
    DDSTextSubtitle {
        color: $boost;
    }
    """


class DDSTextList(DDSTextItem):
    """A container widget for a text list."""
    def __init__(self, list_items: list[str], *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.list_items = list_items


    def compose(self) -> ComposeResult:
        yield Static(self.get_list_string(self.list_items))

    def get_list_string(self, list_items: list[str]) -> str:
        """Get a string representation of the list items."""
        return "\n".join([f" • {item}" for item in list_items])

