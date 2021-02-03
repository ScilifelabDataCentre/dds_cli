""""""


###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import pathlib
import sys

# Installed

# Own modules


class DDSDirectory:
    """Data Delivery System directory class."""

    def __init__(self, path=pathlib.Path):

        dirs = {
            "ROOT": path,
            "FILES": path / pathlib.Path("files/"),
            "META": path / pathlib.Path("meta/"),
            "LOGS": path / pathlib.Path("logs/")
        }

        for _, y in dirs.items():
            try:
                y.mkdir(parents=True)
            except OSError as ose:
                sys.exit("The temporary directory {y} could not be created: "
                         f"{ose}")

        self.directories = dirs
