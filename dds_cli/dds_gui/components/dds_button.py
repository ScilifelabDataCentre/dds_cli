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

    ## Styling to mimic the default styling of textual buttons
    DEFAULT_CSS = """
    DDSSkinnyButton {
        width: 100%;
        height: 1;
        padding: 0 1;
        color: $button-foreground;
        background: $surface;
        border: none;
        border-right: tall $surface-lighten-1;
        border-left: tall $surface-darken-1;   
    

    &:focus {
        text-style: $button-focus-text-style;
        background-tint: $foreground 5%;
    }
    &:hover {
        border: none;
        border-right: tall $surface;
        border-left: tall $surface-darken-2;
    }
    &.-active {
        background: $surface;
        border: none;
        border-right: tall $surface-lighten-1;
        border-left: tall $surface-darken-1;
        tint: $background 30%;
    }
    }
    """
