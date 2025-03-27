"""Directory module. Creates the DDS directory during delivery."""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import errno
import logging
import pathlib
import sys
from datetime import datetime
import typing

# Installed
import rich.markup

# Own modules
import dds_cli.utils

###############################################################################
# START LOGGING CONFIG ################################# START LOGGING CONFIG #
###############################################################################

LOG = logging.getLogger(__name__)

###############################################################################
# CLASSES ########################################################### CLASSES #
###############################################################################


class DDSDirectory:
    """Data Delivery System directory class."""

    def __init__(self, path=pathlib.Path, add_file_dir: bool = True, default_log: bool = True, command: list = []):
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

        if default_log:
            default_log_name = self.get_default_log_name(command=command if command else ["commandnotfound"])
            
            # Start logging to file 
            file_handler = dds_cli.utils.setup_logging_to_file(filename=default_log_name)
            LOG.addHandler(file_handler)
            LOG.debug("Command: %s", " ".join(command))

    def get_default_log_name(self, command: list):
            # Include command in log file name
            # Do not include source in file name
            # Could e.g. be a very long file name --> errors
            command_for_file_name = command.copy()
            source_options: typing.List = ["-s", "--source", "-spf", "--source-path-file"]
            for s in source_options:
                indexes = [i for i, x in enumerate(command_for_file_name) if x == s]
                for i in indexes:
                    command_for_file_name[i+1] = "x"

            # Remove leading - from options
            command_for_file_name = [i.lstrip("-") for i in command_for_file_name[1::]]

            # Format log file path name to contain command
            command_for_file_name: str = "dds_" + "_".join(command_for_file_name).replace("/", "_").replace(
                "\\", "_"
            )

            # Include time stamp in file name
            timestamp_string: str = datetime.now().strftime("%Y%m%d-%H%M%S")

            # Final log name
            log_file = str(
                self.directories["LOGS"] / pathlib.Path(command_for_file_name + "_" + timestamp_string + ".log")
            )

            return log_file
    