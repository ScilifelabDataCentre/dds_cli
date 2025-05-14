"""User Access Widget"""

from typing import Any
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Label

class UserAccess(Widget):
    """A widget for user access."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        
    def compose(self) -> ComposeResult:
        yield Label("User Access")
        