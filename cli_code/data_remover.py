"""Data Remover -- Removes files from projects."""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard Library
import logging
import pathlib
import sys
import traceback
import os

# Installed
import requests
from rich.markdown import Markdown
from rich.layout import Layout
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

        console = rich.console.Console()
        if not response.ok:
            console.print(
                f"Failed to delete files in project: {response.text}")
            os._exit(os.EX_OK)

        # Print out response - deleted or not?
        resp_json = response.json()
        if resp_json["removed"]:
            console.print(
                f"All files have been removed from project {self.project}."
            )
        else:
            if "error" not in resp_json:
                sys.exit("No error message returned despite failure.")

            console.print(resp_json["error"])

    def remove_file(self, files):
        """Remove specific files."""

        response = requests.delete(DDSEndpoint.REMOVE_FILE,
                                   json=files,
                                   headers=self.token)

        console = rich.console.Console()
        if not response.ok:
            console.print(
                f"Failed to delete file(s) '{files}' in project {self.project}:"
                f" {response.text}"
            )
            os._exit(os.EX_OK)

        # Make sure required info is returned
        resp_json = response.json()
        if not all(x in resp_json for x in
                   ["successful", "not_exists", "not_removed"]):
            console.print("No information returned. Server error.")
            os._exit(os.EX_OK)

        message = ""

        # List of successfully deleted files
        if resp_json["successful"]:
            # Get list of files
            deleted_files = resp_json["successful"]

            # Only one line if only one file
            if len(deleted_files) == 1:
                message = f"**File deleted:** {deleted_files[0]}"
            else:
                message = ("**Deleted files:**\n" +
                           "\n".join(f"* {x}" for x in deleted_files))

            md = Markdown(message)
            console.print(rich.padding.Padding(md, 2))

        # Create list of files which were not found in the database
        if resp_json["not_exists"]:
            # Get list of files
            nonexistent_files = resp_json["not_exists"]

            # Only one line if only one file
            if len(nonexistent_files) == 1:
                message = f"**No such file:** {nonexistent_files[0]}"
            else:
                message = ("**No such files:**\n" +
                           "\n".join(f"""* {x}""" for x in nonexistent_files))

            md = Markdown(message)
            console.print(rich.padding.Padding(md, 2))

        # Create table for files which were not deleted
        if resp_json["not_removed"]:
            # Get file dict
            error_files = resp_json["not_removed"]

            if len(error_files) == 1:
                info = list(error_files.items())[0]
                message = (
                    f"**_ERROR_** \t **File not deleted:** {info[0]}"
                    f"\t-\t*{info[1]}*")
                md = Markdown(message)
                console.print(rich.padding.Padding(md, 2))
            else:
                table = rich.table.Table(title="Files not deleted",
                                         show_header=True, header_style="bold")
                _ = [table.add_column(x) for x in ["File name", "Error"]]

                _ = [table.add_row(f, v["error"])
                     for f, v in resp_json["not_removed"].items()]

                console.print(rich.padding.Padding(table, 2))

    def remove_folder(self, folder):
        """Remove specific folders."""

        response = requests.delete(DDSEndpoint.REMOVE_FOLDER,
                                   json=folder,
                                   headers=self.token)

        console = rich.console.Console()
        if not response.ok:
            console.print(
                f"Failed to delete folder(s) '{folder}' "
                f"in project {self.project}: {response.text}"
            )
            os._exit(os.EX_OK)

        # Make sure required info is returned
        resp_json = response.json()
        log.debug(resp_json)

        # if not all(x in resp_json for x in
        #            ["successful", "not_exists", "not_removed"]):
        #     console.print("No information returned. Server error.")
        #     os._exit(os.EX_OK)
