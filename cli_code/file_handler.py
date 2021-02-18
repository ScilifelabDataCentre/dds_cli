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

# Installed

# Own modules
from cli_code import status
from cli_code import DDSEndpoint

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
            log.debug("%s : %s\n", x, y)

    def get_existing_files(self, project, token):
        """Do API call and check for the files in the DB,
        cancels those existing in the DB."""

        args = {"project": project}
        files = list(y["name_in_db"] for _, y in self.data.items())
        log.debug(files)

        response = requests.get(DDSEndpoint.FILE_MATCH, params=args,
                                headers=token, json=files)

        if not response.ok:
            sys.exit("Failed to match previously uploaded files."
                     f"{response.status_code} -- {response.text}")

        files_not_in_db = response.json()

        log.debug("Files not in db: %s", files_not_in_db)
        if "files" not in files_not_in_db:
            sys.exit("Files not returned from API.")

        if files_not_in_db["files"] is None:
            return set()
        # if set(files_not_in_db["files"]) == set(files):
        #     self.failed = self.data
        #     self.data = {}
        #     sys.exit("All specified files have already been uploaded.")

        log.debug("Files not in db: %s", files_not_in_db["files"])

        # Return files to cancel
        return set(files).difference(set(files_not_in_db["files"]))

    def collect_file_info_local(self, all_paths, folder=None):
        """Get info on each file in each path specified."""

        file_info = dict()

        for path in all_paths:
            # Get info for all files
            # and feed back to same function for all folders
            if path.is_file():
                subpath = self.compute_subpath(file=path, folder=folder)
                file_info[path] = {
                    "subpath": subpath,
                    "name_in_bucket": self.generate_bucket_filepath(
                        filename=path.name,
                        folder=folder
                    ),
                    "name_in_db": str(subpath / path.name)
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
