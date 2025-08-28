"""DDS Text Item"""

from typing import Any
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
