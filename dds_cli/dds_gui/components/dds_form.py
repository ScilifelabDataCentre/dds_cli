"""DDS Form Widget"""

from typing import Any
from textual.containers import Container


class DDSForm(Container):
    """A widget for the form."""

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)

    ## Additional styling on the input fields to combat wierd default alignment
    DEFAULT_CSS = """
    DDSForm {
        height: auto;
        max-width: 100;
    }
    DDSForm > * {
        margin: 1;
    }

    DDSForm > DDSInput {
        margin: 1 1 1 0;

    }
    """
