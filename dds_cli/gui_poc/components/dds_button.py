"""DDS Button Widget"""
from typing import Any
from textual.widgets import Button

class DDSButton(Button):
    """A button widget with a border and title for the GUI.
    Args:
        label: The label to be displayed on the button.
    """
    def __init__(self, label: str, *args: Any, **kwargs: Any) -> None:
        super().__init__(label.upper(), *args, **kwargs)
