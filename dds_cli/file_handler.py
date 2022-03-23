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
    def append_errors_to_file(log_file: pathlib.Path, file, info, status):
        """Save errors to specific json file."""
        # Use log file last on the list
        log_file_to_use = log_file[-1]

        try:
            # Create file if it doesn't exist
            if not log_file_to_use.exists():
                with log_file_to_use.open(mode="w+") as file_obj:
                    json.dump({}, file_obj)

            # Switch to new file if current file is "too large"
            if log_file_to_use.stat().st_size > 4e6:
                log_file_to_use = log_file_to_use.with_name(str(len(log_file)) + log_file[0].name)

            # Keep file as correct json by loading and "appending"
            with log_file_to_use.open(mode="r+") as json_file:
                file_data = json.load(json_file)
                file_data[str(file)] = {
                    **FileHandler.make_json_serializable(non_json=info),
                    "status": FileHandler.make_json_serializable(non_json=status),
                }
                json_file.seek(0)
                json.dump(file_data, json_file, indent=4)

        except (OSError, TypeError) as err:
            LOG.warning(str(err))

        return log_file_to_use

    @staticmethod
    def make_json_serializable(non_json):
        """Convert pathlib.Path instances in dict to string."""
        return {str(x): (str(y) if isinstance(y, pathlib.Path) else y) for x, y in non_json.items()}

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
