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

    @property
    def text_selection(self):
        """Override text_selection to handle NoScreen error gracefully."""
        try:
            return super().text_selection
        except Exception:
            # Handle NoScreen error during app unmount
            return None

    def render_line(self, y: int):
        """Override render_line to handle rendering errors gracefully."""
        try:
            return super().render_line(y)
        except Exception:
            # Handle rendering errors during app unmount
            # Return a simple empty line
            from textual.geometry import Region
            from textual.strip import Strip
            return Strip([], Region(0, y, 0, 1))

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

    @property
    def text_selection(self):
        """Override text_selection to handle NoScreen error gracefully."""
        try:
            return super().text_selection
        except Exception:
            # Handle NoScreen error during app unmount
            return None

    def render_line(self, y: int):
        """Override render_line to handle rendering errors gracefully."""
        try:
            return super().render_line(y)
        except Exception:
            # Handle rendering errors during app unmount
            # Return a simple empty line
            from textual.geometry import Region
            from textual.strip import Strip
            return Strip([], Region(0, y, 0, 1))

    ## Styling to mimic the default styling of textual buttons
    DEFAULT_CSS = """
        DDSSkinnyButton {
            width: 100%;
        }
    """
