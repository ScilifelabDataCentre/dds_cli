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
                y.mkdir(parents=True)
            except OSError as ose:
                sys.exit("The temporary directory {y} could not be created: " f"{ose}")

        self.directories = dirs
