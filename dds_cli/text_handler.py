"""Handles formatting of string."""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import logging
import pathlib
import dds_cli

# Installed

# Own modules

###############################################################################
# START LOGGING CONFIG ################################# START LOGGING CONFIG #
###############################################################################

LOG = logging.getLogger(__name__)

###############################################################################
# CLASSES ########################################################### CLASSES #
###############################################################################


class StringFormat:
    """Defines different formats for strings, e.g. colors and bold."""

    HEADER = "\033[95m"
    PURPLE = "\033[95m"
    CYAN = "\033[96m"
    DARKCYAN = "\033[36m"
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    END = "\033[0m"


class TextHandler(StringFormat):
    """Handler for text formatting."""

    # Static methods ############ Static methods #
    @staticmethod
    def format_tabs(string_len, max_string_len, tab_len=4):
        """Format number of tabs to have within string."""

        tab = " " * (max_string_len - string_len + tab_len)

        return tab

    @staticmethod
    def task_name(file, step="", max_len=30):
        """Generate display name for progress task"""

        task_name = file

        # Keep full file name in progress if short otherwise add ... in the beginning
        if len(str(file)) > max_len:
            file_name = pathlib.Path(file).name
            task_name = f".../{file_name}"
            if len(task_name) > max_len:
                task_name = "..." + task_name.split("...", 1)[-1][-max_len::]

        # Different symbols to the left depending on current process
        if dds_cli.dds_on_legacy_console:
            symbols = {
                "encrypt": "[bold]encrypt",
                "put": "[bold]put",
                "get": "[bold]get",
                "decrypt": "[bold]decrypt",
            }
        else:
            symbols = {
                "encrypt": ":lock:",
                "put": ":arrow_up:",
                "get": ":arrow_down:",
                "decrypt": ":unlock:",
            }
        return f"{symbols.get(step, '')} {task_name}"
