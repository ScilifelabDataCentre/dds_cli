"""File handler module. Base class for LocalFileHandler and RemoteFileHandler."""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import json
import logging
import os
import pathlib

# Installed

# Own modules
import dds_cli.utils
import dds_cli.exceptions

###############################################################################
# START LOGGING CONFIG ################################# START LOGGING CONFIG #
###############################################################################

LOG = logging.getLogger(__name__)

###############################################################################
# CLASSES ########################################################### CLASSES #
###############################################################################


class FileHandler:
    """Main file handler."""

    def __init__(self, user_input, local_destination, project=None):
        """Initiate file handler."""
        source, source_path_file = user_input

        # Get user specified data
        self.project = project
        self.local_destination = local_destination
        self.data_list = []
        if source is not None:
            self.data_list += list(source)
        if source_path_file is not None:
            source_path_file = pathlib.Path(source_path_file)
            if source_path_file.exists():
                try:
                    with source_path_file.resolve().open(mode="r") as spf:
                        self.data_list += spf.read().splitlines()
                except OSError as err:
                    dds_cli.utils.console.print(
                        f"Failed to get files from source-path-file option: {err}"
                    )
                    os._exit(1)

        self.failed = {}

    # Static methods ############ Static methods #
    @staticmethod
    def append_errors_to_file(file: pathlib.Path, info):
        """Save errors to specific json file."""
        try:
            with file.open(mode="a") as errfile:
                json_output = json.dumps(
                    info,
                    indent=None,
                )
                # Each line is valid json, but the entire file is not.
                # Multiple threads are appending to this file, so valid json for
                # the entire file is not trivial.
                errfile.write(json_output + "\n")
        except (OSError, TypeError) as err:
            LOG.warning(str(err))

    @staticmethod
    def delete_tempdir(directory: pathlib.Path):
        """Delete the specified directory."""
        ok_to_remove = False

        # If file not ok to remove folder
        if not directory.is_dir():
            return ok_to_remove

        # Iterate through any existing subdirectories - recursive
        LOG.debug(f"Any in directory? {any(directory.iterdir())}")
        for x in directory.iterdir():
            LOG.debug(x)
        if any(directory.iterdir()):
            for p in directory.iterdir():
                if p.is_dir():
                    ok_to_remove = FileHandler.delete_tempdir(directory=p)
                    if ok_to_remove:
                        directory.rmdir()
        else:
            directory.rmdir()
            ok_to_remove = True

        return ok_to_remove
