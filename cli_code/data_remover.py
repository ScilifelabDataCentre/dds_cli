"""Data Remover -- Removes files from projects."""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard Library
import logging
import pathlib
import sys
import traceback

# Installed
import requests
import rich

# Own modules
from cli_code import base
from cli_code import DDSEndpoint

###############################################################################
# START LOGGING CONFIG ################################# START LOGGING CONFIG #
###############################################################################

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

###############################################################################
# CLASSES ########################################################### CLASSES #
###############################################################################


class DataRemover(base.DDSBaseClass):
    """Data remover class."""

    def __init__(self, project: str, username: str = None,
                 config: pathlib.Path = None):

        # Initiate DDSBaseClass to authenticate user
        super().__init__(username=username, config=config, project=project)

        # Only method "ls" can use the DataLister class
        if self.method != "rm":
            sys.exit(f"Unauthorized method: {self.method}")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if exc_type is not None:
            traceback.print_exception(exc_type, exc_value, tb)
            return False  # uncomment to pass exception through

        return True

    def remove_all(self):
        """Remove all files in project."""

        # Perform request to API to perform deletion
        response = requests.delete(DDSEndpoint.REMOVE_PROJ_CONT,
                                   headers=self.token)

        if not response.ok:
            sys.exit(f"Failed to delete files in project {self.project}: "
                     f"{response.status_code} -- {response.text}")

        # Print out response - deleted or not?
        resp_json = response.json()
        console = rich.console.Console()
        if resp_json["removed"]:
            console.print(
                f"All files have been removed from project {self.project}."
            )
        else:
            if "message" not in resp_json:
                sys.exit("No error message returned despite failure.")

            console.print(resp_json["message"])

    def remove_file(self, files):
        """Remove specific files."""

        response = requests.delete(DDSEndpoint.REMOVE_FILE,
                                   json=files,
                                   headers=self.token)

        if not response.ok:
            sys.exit(
                f"Failed to delete file '{files}' in project {self.project}: "
                f"{response.status_code} -- {response.text}"
            )

        log.debug(response.json())

    def remove_folder(self):
        """Remove specific folders."""
