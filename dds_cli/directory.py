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
            # Include command in log file name
            if not command:
                command_as_string = "command_not_found"
            else:
                # Format log file path name to contain command and timestamp
                command_as_string: str = "dds_" + "_".join(command).replace("/", "_").replace(
                    "\\", "_"
                )
            
            # Include time stamp in file name
            timestamp_string: str = datetime.now().strftime("%Y%m%d-%H%M%S")

            # Final log name
            log_file = str(
                dirs["LOGS"] / pathlib.Path(command_as_string + "_" + timestamp_string + ".log")
            )

            # Start logging to file 
            log_fh = logging.FileHandler(log_file, encoding="utf-8")
            log_fh.setLevel(logging.DEBUG)
            log_fh.setFormatter(
                logging.Formatter(
                    fmt="[%(asctime)s] %(name)-15s %(lineno)-5s [%(levelname)-7s]  %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )
            )
            LOG.addHandler(log_fh)