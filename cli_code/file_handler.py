"""File handler module"""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import logging
import sys
import pathlib
import uuid
import requests
import dataclasses
import functools

# Installed

# Own modules
from cli_code import status
from cli_code import DDSEndpoint
from cli_code import s3_connector as s3

###############################################################################
# START LOGGING CONFIG ################################# START LOGGING CONFIG #
###############################################################################

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

###############################################################################
# CLASSES ########################################################### CLASSES #
###############################################################################


@dataclasses.dataclass
class FileHandler:
    """Collects the files specified by the user."""

    user_input: dataclasses.InitVar[dict]
    data: dict = dataclasses.field(init=False)
    failed: dict = dataclasses.field(init=False)

    def __post_init__(self, user_input):

        source, source_path_file, *_ = user_input

        # Get user specified data
        data_list = list()
        if source is not None:
            data_list += list(source)
        if source_path_file is not None:
            source_path_file = pathlib.Path(source_path_file)
            if source_path_file.exists():
                with source_path_file.resolve().open(mode="r") as spf:
                    data_list += spf.read().splitlines()

        # Get absolute paths to all data and removes duplicates
        data_list = list(set(pathlib.Path(x).resolve() for x in data_list
                             if pathlib.Path(x).exists()))

        # Quit if no data
        if not data_list:
            sys.exit("No data specified.")

        self.data = self.collect_file_info_local(all_paths=data_list)
        self.failed = {}

        for x, y in self.data.items():
            log.debug("\n%s : %s\n", x, y)

    def create_status_dict(self, to_cancel):
        """Create dict for tracking file delivery status"""

        status_dict = {}
        for x in list(self.data):
            cancel = bool(x in to_cancel)
            if cancel:
                self.failed[x] = {**self.data.pop(x),
                                  **{"message": "File already uploaded"}}
            else:
                status_dict[x] = {
                    "cancel": False,
                    "message": "",
                    "put": {"started": False, "done": False},
                    "add_file_db": {"started": False, "done": False}
                }

        log.debug(status_dict)
        return status_dict

    def collect_file_info_local(self, all_paths, folder=None):
        """Get info on each file in each path specified."""

        file_info = dict()

        for path in all_paths:
            # Get info for all files
            # and feed back to same function for all folders
            if path.is_file():
                subpath = self.compute_subpath(file=path, folder=folder)
                file_info[str(subpath / path.name)] = {
                    "path_local": path,
                    "subpath": subpath,
                    "name_in_bucket": self.generate_bucket_filepath(
                        filename=path.name,
                        folder=folder
                    )
                    # "name_in_db": str(subpath / path.name)
                }
            elif path.is_dir():
                file_info.update({
                    **self.collect_file_info_local(all_paths=path.glob("**/*"),
                                                   folder=path.name)
                })

        return file_info

    def generate_bucket_filepath(self, filename="", folder=None):
        """Generates filename and new path which the file will be
        called in the bucket."""

        # Set path to file
        directory = pathlib.Path("") if folder is None \
            else pathlib.Path(folder)

        # Generate new file name
        new_name = "".join([str(uuid.uuid4().hex[:6]), "_", filename])

        return str(directory / pathlib.Path(new_name))

    def compute_subpath(self, file, folder):
        """Computes the path to the file, from the specified folder."""

        subdir = pathlib.Path("")
        if folder is not None:
            fileparts = file.parts
            start_ind = fileparts.index(folder)
            subdir = pathlib.Path(*fileparts[start_ind:-1])

        return subdir

    def cancel_all(self):
        """Cancel upload of all files"""

    def cancel_one(self):
        """Cancel the failed file"""
