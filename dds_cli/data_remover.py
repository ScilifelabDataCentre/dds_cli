"""Data Remover -- Removes files from projects."""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard Library
import logging
import pathlib

# Installed
import requests
import rich
import rich.markup
import rich.table
import rich.padding
import simplejson

# Own modules
import dds_cli
from dds_cli.custom_decorators import removal_spinner
from dds_cli import base
from dds_cli import DDSEndpoint

###############################################################################
# START LOGGING CONFIG ################################# START LOGGING CONFIG #
###############################################################################

LOG = logging.getLogger(__name__)

###############################################################################
# CLASSES ########################################################### CLASSES #
###############################################################################


class DataRemover(base.DDSBaseClass):
    """Data remover class."""

    def __init__(
        self,
        project: str,
        method: str = "rm",
        no_prompt: bool = False,
        token_path: str = None,
    ):
        """Handle actions regarding data deletion in the cli."""
        # Initiate DDSBaseClass to authenticate user
        super().__init__(
            project=project,
            method=method,
            no_prompt=no_prompt,
            token_path=token_path,
        )

        self.failed_table = None
        self.failed_files = None

        # Only method "rm" can use the DataRemover class
        if self.method != "rm":
            raise dds_cli.exceptions.InvalidMethodError(
                attempted_method=method, message="DataRemover attempting unauthorized method"
            )

    def __create_failed_table(self, resp_json, level="File"):
        """Output a response after deletion."""
        # Check that enough info
        if not all(x in resp_json for x in ["not_exists", "not_removed"]):
            raise dds_cli.exceptions.APIError(
                f"Malformatted response detected when attempting remove action on {self.project}."
            )

        # Get info
        not_exists = resp_json["not_exists"]
        delete_failed = resp_json["not_removed"]

        # Create table if any files failed
        if not_exists or delete_failed:
            if self.no_prompt:
                self.failed_files = {"Errors": []}
                for x in not_exists:
                    self.failed_files["Errors"].append({x: f"No such {level.lower()}"})
                for x, y in delete_failed.items():
                    self.failed_files["Errors"].append({x: y})
            else:
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
                for x in not_exists:
                    table.add_row(rich.markup.escape(x), f"No such {level.lower()}")

                for x, y in delete_failed.items():
                    table.add_row(
                        f"[light_salmon3]{rich.markup.escape(x)}[/light_salmon3]",
                        f"[light_salmon3]{rich.markup.escape(y)}[/light_salmon3]",
                    )

                # Print out table
                self.failed_table = rich.padding.Padding(table, 1)

    @staticmethod
    def delete_tempfile(file: pathlib.Path):
        """Delete the specified file."""
        try:
            file.unlink()
        except FileNotFoundError as err:
            LOG.exception(str(err))
            LOG.warning("File deletion may have failed. Usage of space may increase.")

    # Public methods ###################### Public methods #
    @removal_spinner
    def remove_all(self, *_, **__):
        """Remove all files in project."""
        # Perform request to API to perform deletion
        try:
            response = requests.delete(
                DDSEndpoint.REMOVE_PROJ_CONT, params={"project": self.project}, headers=self.token
            )
        except requests.exceptions.RequestException as err:
            raise SystemExit from err

        if not response.ok:
            raise dds_cli.exceptions.APIError(f"Failed to delete files in project: {response.text}")

        # Print out response - deleted or not?
        try:
            resp_json = response.json()
        except simplejson.JSONDecodeError as err:
            raise SystemExit from err

        if "removed" not in resp_json:
            raise dds_cli.exceptions.APIError(
                "Malformatted response detected when attempting "
                f"to remove all files from {self.project}."
            )

    @removal_spinner
    def remove_file(self, files):
        """Remove specific files."""
        try:
            response = requests.delete(
                DDSEndpoint.REMOVE_FILE,
                params={"project": self.project},
                json=files,
                headers=self.token,
            )
        except requests.exceptions.RequestException as err:
            raise SystemExit from err

        if not response.ok:
            raise dds_cli.exceptions.APIError(
                f"Failed to delete file(s) '{files}' in project {self.project}: {response.text}"
            )

        # Get info in response
        try:
            resp_json = response.json()
        except simplejson.JSONDecodeError as err:
            raise SystemExit from err

        self.__create_failed_table(resp_json=resp_json)

    @removal_spinner
    def remove_folder(self, folder):
        """Remove specific folders."""
        try:
            response = requests.delete(
                DDSEndpoint.REMOVE_FOLDER,
                params={"project": self.project},
                json=folder,
                headers=self.token,
            )
        except requests.exceptions.RequestException as err:
            raise SystemExit from err

        if not response.ok:
            raise dds_cli.exceptions.APIError(
                f"Failed to delete folder(s) '{folder}' "
                f"in project {self.project}: {response.text}"
            )

        # Make sure required info is returned
        try:
            resp_json = response.json()
        except simplejson.JSONDecodeError as err:
            raise SystemExit from err

        self.__create_failed_table(resp_json=resp_json, level="Folder")

        if resp_json.get("nr_deleted"):
            LOG.info(f"{resp_json['nr_deleted']} files were successfully deleted in {folder}.")
        # Print extra warning if s3 deletion succeeded, db failed
        if resp_json.get("fail_type") == "db":
            LOG.error(
                "Some files were deleted, but their database entries were not. "
                + "Try to run the command again, and contact Data Centre if the problem persists."
            )
