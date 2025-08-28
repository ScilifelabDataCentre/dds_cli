"""DDS Input Widget"""

from typing import Any

from textual.widgets import Input


class DDSInput(Input):
    """A widget for the input field."""

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)

    DEFAULT_CSS = """
    DDSInput {
        margin: 0 0 1 -1;

    }
    """
