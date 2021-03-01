"""Handles formatting of string."""


class StringFormat:
    """Defines different formats for strings, e.g. colors and bold."""

    HEADER = '\033[95m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    DARKCYAN = '\033[36m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'


class TextHandler(StringFormat):
    """Handler for text formatting."""

    @staticmethod
    def format_tabs(string_len, max_string_len, tab_len=4):
        """Format number of tabs to have within string."""

        tab = " " * (max_string_len-string_len+tab_len)

        return tab
