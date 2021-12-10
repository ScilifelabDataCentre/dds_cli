"""Directory module. Creates the DDS directory during delivery."""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import logging
import os
import pathlib
import sys

# Installed

# Own modules

###############################################################################
# START LOGGING CONFIG ################################# START LOGGING CONFIG #
###############################################################################

LOG = logging.getLogger(__name__)

###############################################################################
# CLASSES ########################################################### CLASSES #
###############################################################################


class DDSDirectory:
    """Data Delivery System directory class."""

    def __init__(self, path=pathlib.Path, add_file_dir: bool = True):

        dirs = {
            "ROOT": path,
            "META": path / pathlib.Path("meta/"),
            "LOGS": path / pathlib.Path("logs/"),
        }

        if add_file_dir:
            dirs["FILES"] = path / pathlib.Path("files/")

        for _, y in dirs.items():
            try:
                y.mkdir(parents=True, exist_ok=False)
            except OSError as ose:
                sys.exit("The temporary directory {y} could not be created: " f"{ose}")

        self.directories = dirs
