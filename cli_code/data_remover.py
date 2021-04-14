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
import rich
import simplejson

# Own modules
from cli_code import base
from cli_code import data_lister
from cli_code import DDSEndpoint
from cli_code.cli_decorators import removal_spinner

###############################################################################
# START LOGGING CONFIG ################################# START LOGGING CONFIG #
###############################################################################

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)

###############################################################################
# CLASSES ########################################################### CLASSES #
###############################################################################


class DataRemover(base.DDSBaseClass):
    """Data remover class."""

    def __init__(self, project: str, username: str = None, config: pathlib.Path = None):

        # Initiate DDSBaseClass to authenticate user
        super().__init__(username=username, config=config, project=project)

        # Only method "ls" can use the DataLister class
        if self.method != "rm":
            sys.exit(f"Unauthorized method: {self.method}")

    # def __enter__(self):
    #     return self

    # def __exit__(self, exc_type, exc_value, tb):
    #     if exc_type is not None:
    #         traceback.print_exception(exc_type, exc_value, tb)
    #         return False  # uncomment to pass exception through

    #     return True

    @removal_spinner
    def remove_all(self, *_, **kwargs):
        """Remove all files in project."""

        message = ""

        # Perform request to API to perform deletion
        try:
            response = requests.delete(DDSEndpoint.REMOVE_PROJ_CONT, headers=self.token)
        except requests.exceptions.RequestException as err:
            raise SystemExit from err

        if not response.ok:
            return f"Failed to delete files in project: {response.text}"

        # Print out response - deleted or not?
        try:
            resp_json = response.json()
        except simplejson.JSONDecodeError as err:
            raise SystemExit from err

        if resp_json["removed"]:
            message = f"All files have been removed from project {self.project}."
        else:
            message = resp_json.get("error")
            if message is None:
                message = "No error message returned despite failure."

        return message

    @removal_spinner
    def remove_file(self, files):
        """Remove specific files."""

        try:
            response = requests.delete(
                DDSEndpoint.REMOVE_FILE, json=files, headers=self.token
            )
        except requests.exceptions.RequestException as err:
            raise SystemExit from err

        if not response.ok:
            return (
                f"Failed to delete file(s) '{files}' in project {self.project}:"
                f" {response.text}"
            )

        # Get info in response
        try:
            resp_json = response.json()
        except simplejson.JSONDecodeError as err:
            raise SystemExit from err

        return self.__response_delete(resp_json=resp_json)

    @removal_spinner
    def remove_folder(self, folder):
        """Remove specific folders."""

        try:
            response = requests.delete(
                DDSEndpoint.REMOVE_FOLDER, json=folder, headers=self.token
            )
        except requests.exceptions.RequestException as err:
            raise SystemExit from err

        if not response.ok:
            return (
                f"Failed to delete folder(s) '{folder}' "
                f"in project {self.project}: {response.text}"
            )

        # Make sure required info is returned
        try:
            resp_json = response.json()
        except simplejson.JSONDecodeError as err:
            raise SystemExit from err

        return self.__response_delete(resp_json=resp_json, level="Folder")

    @staticmethod
    def __response_delete(resp_json, level="File"):
        """Output a response after deletion."""

        # console = rich.console.Console()

        # Check that enough info
        if not all(x in resp_json for x in ["not_exists", "not_removed"]):
            return "No information returned. Server error."
            # os._exit(os.EX_OK)

        # Get info
        not_exists = resp_json["not_exists"]
        delete_failed = resp_json["not_removed"]

        # Create table if any files failed
        if not_exists or delete_failed:
            # Warn if many failed files
            data_lister.DataLister.warn_if_many(
                count=len(not_exists) + len(delete_failed)
            )

            # Create table and add columns
            table = rich.table.Table(
                title=f"{level}s not deleted",
                title_justify="left",
                show_header=True,
                header_style="bold",
            )
            columns = [level, "Error"]
            for x in columns:
                table.add_column(x)

            # Add rows
            _ = [table.add_row(x, f"No such {level.lower()}") for x in not_exists]
            _ = [
                table.add_row(
                    f"[light_salmon3]{x}[/light_salmon3]",
                    f"[light_salmon3]{y}[/light_salmon3]",
                )
                for x, y in delete_failed.items()
            ]

            # Print out table
            return rich.padding.Padding(table, 1)

    @staticmethod
    def delete_tempfile(file: pathlib.Path):
        """Deletes the specified file."""

        try:
            file.unlink()
        except Exception as err:
            # except FileNotFoundError as err:
            LOG.exception(str(err))
