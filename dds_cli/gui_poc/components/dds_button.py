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

    DEFAULT_CSS = """
    DDSButton {
        padding: 0 2 0 2;
    }
    DDSButton.wide {
        width: 100%;
    }
    """

class DDSFormButton(DDSButton):
    """A button widget for the form."""
    def __init__(self, label: str, *args: Any, **kwargs: Any) -> None:
        super().__init__(label.upper(), *args, **kwargs)

    ## Styling to mimic the default styling of textual buttons
    DEFAULT_CSS = """
    DDSFormButton {
       background: $secondary;
       border-top: tall $secondary-lighten-3;
       border-bottom: tall $secondary-darken-3;
    }
    DDSFormButton:hover {
       background: $secondary-darken-2;
       border-top: tall $secondary 
    }
    DDSFormButton.-active {
       background: $secondary;
       border-top: tall $secondary-darken-3;
       border-bottom: tall $secondary-lighten-3;
    }
    """

class DDSSkinnyButton(Button):
    """A skinny button widget."""
    def __init__(self, label: str, *args: Any, **kwargs: Any) -> None:
        super().__init__(label.capitalize(), *args, **kwargs)

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
