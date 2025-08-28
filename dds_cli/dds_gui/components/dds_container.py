"""DDS Container Widgets"""

from typing import Any
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.reactive import Reactive


class DDSContainer(VerticalScroll):
    """A contianer widget with border and title for wrapping main content in the GUI.
    Args:
        title: The title to be displayed in the border of the container.
    """

    def __init__(self, title: str, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.border_title = title.upper()

    subtitle: Reactive[str] = Reactive(None, recompose=False)

    DEFAULT_CSS = """
    DDSContainer {
        border: round $primary; 
        padding: 1;
        scrollbar-size: 1 1;
        scrollbar-color: $primary 70%;
    }

    DDSContainer.accent {   
        border: round $accent;
    }
   """

    def watch_subtitle(self, subtitle: str) -> None:
        """Watch the subtitle reactive variable and update the border subtitle."""
        self.border_subtitle = subtitle


class DDSContentContainer(Vertical):
    """A container widget with no border for wrapping widgets in the GUI. Ensures that all content is visible."""

    DEFAULT_CSS = """
    DDSContentContainer {
        width: 100%;
        height: auto;
    }
    """


class DDSSpacedContainer(VerticalScroll):
    """A container widget with vertical spacing between child widgets."""

    DEFAULT_CSS = """
    DDSSpacedContainer {
        align: center top;
        scrollbar-size: 1 1;
        scrollbar-color: $primary 80%;
        scrollbar-color-active: $primary;
        scrollbar-color-hover: $primary;
    }

    DDSSpacedContainer > * {
        margin-bottom: 1;
    }

    
    """


class DDSSpacedHorizontalContainer(Horizontal):
    """A container widget with horizontal spacing between child widgets."""

    DEFAULT_CSS = """
    DDSSpacedHorizontalContainer {
        align: left top;
    }

    DDSSpacedHorizontalContainer > * {
        margin-right: 2;
    }
    """
