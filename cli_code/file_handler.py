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

# Own modules

###############################################################################
# START LOGGING CONFIG ################################# START LOGGING CONFIG #
###############################################################################

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)

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

        configpath = pathlib.Path(configfile).resolve()
        if not configpath.exists():
            sys.exit("Config file does not exist.")

        try:
            original_umask = os.umask(0)
            with configpath.open(mode="r") as cfp:
                contents = json.load(cfp)
        except json.decoder.JSONDecodeError as err:
            sys.exit(f"Failed to get config file contents: {err}")
        finally:
            os.umask(original_umask)

        return contents
