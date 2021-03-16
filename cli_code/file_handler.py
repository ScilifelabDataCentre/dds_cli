"""File handler module. Base class for LocalFileHandler and RemoteFileHandler."""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import logging
import sys
import pathlib
import os
import json

# Installed
import rich

# Own modules

###############################################################################
# START LOGGING CONFIG ################################# START LOGGING CONFIG #
###############################################################################

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)

###############################################################################
# RICH CONFIG ################################################### RICH CONFIG #
###############################################################################

console = rich.console.Console()

###############################################################################
# CLASSES ########################################################### CLASSES #
###############################################################################


class FileHandler:
    """Main file handler."""

    def __init__(self, user_input):
        source, source_path_file = user_input

        # Get user specified data
        self.data_list = list()
        if source is not None:
            self.data_list += list(source)
        if source_path_file is not None:
            source_path_file = pathlib.Path(source_path_file)
            if source_path_file.exists():
                with source_path_file.resolve().open(mode="r") as spf:
                    self.data_list += spf.read().splitlines()

        self.failed = {}

    @staticmethod
    def extract_config(configfile):
        """Extracts info from config file."""

        # Absolute path to config file
        configpath = pathlib.Path(configfile).resolve()
        if not configpath.exists():
            console.print("\n:warning: Config file does not exist. :warning:\n")
            os._exit(os.EX_OK)

        # Open config file and get contents
        try:
            original_umask = os.umask(0)
            with configpath.open(mode="r") as cfp:
                contents = json.load(cfp)
        except json.decoder.JSONDecodeError as err:
            console.print(f"\nFailed to get config file contents: {err}\n")
            os._exit(os.EX_OK)
        finally:
            os.umask(original_umask)

        return contents
