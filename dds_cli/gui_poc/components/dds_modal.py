"""DDS Modal Screen."""
from typing import Any
from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Label


class DDSModal(ModalScreen):
    """A modal screen for the GUI."""
    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)

    DEFAULT_CSS = """
    DDSModal {
        background: $background;
        width: 50%;
        height: 50%;
    }
    """
