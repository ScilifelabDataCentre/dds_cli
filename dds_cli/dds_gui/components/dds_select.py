"""DDS Select Widget"""

from typing import List
from textual.widgets import Select


class DDSSelect(Select):
    """A select widget with a title.
    Args:
        title: The title to be displayed in the select widget.
        data: A list of strings to be displayed in the select widget.
    """

    def __init__(self, title: str, data: List[str], *args, **kwargs):
        super().__init__(options=((d, d) for d in data), *args, **kwargs)
        self.prompt = title
        self.type_to_search = True

    DEFAULT_CSS = """
    DDSSelect {
        margin: 0 0 1 -1;
    }
    """
