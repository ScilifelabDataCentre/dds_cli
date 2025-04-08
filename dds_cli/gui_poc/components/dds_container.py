"""DDS Container Widget"""

from typing import Any
from textual.containers import Container, Horizontal, ScrollableContainer, Vertical, VerticalScroll   


class DDSContainer(VerticalScroll):
    """A contianer widget with border and title for wrapping widgets in the GUI.
    Args:
        title: The title to be displayed in the border of the container.
    """

    def __init__(self, title: str,   *args: Any, **kwargs: Any) -> None:
        super().__init__( *args, **kwargs)
        self.border_title = title.upper()
    
    DEFAULT_CSS = """
    DDSContainer {
        border: round $primary; 
        padding: 2;
        scrollbar-size: 1 1;
    }
    DDSContainer.accent {   
        border: round $accent;
    }
   """


class DDSSpacedContainer(Vertical):
    """A container widget with spacing between child widgets."""
    
    DEFAULT_CSS = """
    DDSSpacedContainer {
        align: center top;
    }

    DDSSpacedContainer > * {
        margin-bottom: 1;
    }
    """


class DDSSpacedHorizontalContainer(Horizontal):
    """A container widget with spacing between child widgets."""

    DEFAULT_CSS = """
    DDSSpacedHorizontalContainer {
        align: center top;
    }

    DDSSpacedHorizontalContainer > * {
        margin-right: 1;
    }
    """
