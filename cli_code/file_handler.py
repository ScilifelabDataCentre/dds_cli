"""File handler module"""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import logging
import sys
import pathlib

# Installed

# Own modules

###############################################################################
# START LOGGING CONFIG ################################# START LOGGING CONFIG #
###############################################################################

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)

###############################################################################
# CLASSES ########################################################### CLASSES #
###############################################################################


class FileCollector:
    """Collects the files specified by the user."""

    def __init__(self, user_input):
        
        # Get user specified data
        data_list = list()
        if "source" in user_input and user_input["source"]:
            data_list += list(user_input["source"])
        if "source_path_file" in user_input and \
                user_input["source_path_file"]:
            source_path_file = pathlib.Path(user_input["source_path_file"])
            if source_path_file.exists():
                with source_path_file.resolve().open(mode="r") as spf:
                    data_list += spf.read().splitlines()

        # Get absolute paths to all data and removes duplicates
        data_list = list(set(pathlib.Path(x).resolve() for x in data_list
                     if pathlib.Path(x).exists()))

        # Quit if no data
        if not data_list:
            sys.exit("No data specified.")

        self.data = data_list


