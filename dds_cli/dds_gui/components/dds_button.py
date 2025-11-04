"""DDS Button Widgets"""

from typing import Any
from textual.widgets import Button


class DDSButton(Button):
    """Regular button widget with uppercase title.
    Args:
        label: The label to be displayed on the button.
    """

    def __init__(self, label: str, *args: Any, **kwargs: Any) -> None:
        super().__init__(label.upper(), *args, **kwargs)

    DEFAULT_CSS = """
    DDSButton {
        padding: 0 2 0 2;
    }
    DDSButton.wide {
        width: 100%;
    }
    """


class DDSSkinnyButton(Button):
    """Skinny button widget with capitalized title.
    Args:
        label: The label to be displayed on the button.
    """

    def __init__(self, label: str, *args: Any, **kwargs: Any) -> None:
        super().__init__(label.capitalize(), *args, **kwargs)

    DEFAULT_CSS = """
        DDSSkinnyButton {
            width: 100%;
        }
    """
