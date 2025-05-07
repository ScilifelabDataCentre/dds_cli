"""DDS Select Widget"""
from textual.widgets import Select


class DDSSelect(Select):
    """A select widget with a title."""
    def __init__(self, title: str, data: list[str], *args, **kwargs):
        super().__init__(options=((d, d) for d in data), *args, **kwargs)
        self.prompt = title
        self.type_to_search = True

    DEFAULT_CSS = """
    DDSSelect {
        margin: 0 0 1 -1;
    }
    """
