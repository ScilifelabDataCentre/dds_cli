"""Directory module. Creates the DDS directory during delivery."""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import errno
import logging
import pathlib
import sys

# Installed
import rich.markup

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

    def __init__(
        self,
        path=pathlib.Path,
        add_file_dir: bool = True,
    ):
        # The following subdirs should be included in staging directory
        dirs = {
            "ROOT": path,
            "META": path / pathlib.Path("meta/"),
            "LOGS": path / pathlib.Path("logs/"),
        }

        # files subdir only relevant for some commands
        if add_file_dir:
            dirs["FILES"] = path / pathlib.Path("files/")

        # Create staging directory and subdirectories
        for directory in dirs.values():
            try:
                directory.mkdir(parents=True, exist_ok=False)
            except OSError as err:
                if err.errno == errno.EEXIST:
                    sys.exit(
                        f"Directory '{rich.markup.escape(str(directory))}' already exists. "
                        "Please specify a path where a new folder can be created."
                    )
                else:
                    sys.exit(
                        f"The temporary directory '{rich.markup.escape(str(directory))}' could not be created: {err}"
                    )

        self.directories = dirs
