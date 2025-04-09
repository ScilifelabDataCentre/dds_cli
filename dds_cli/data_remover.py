"""Data Remover -- Removes files from projects."""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard Library
import logging
import pathlib

# Installed
import rich
import rich.markup
import rich.table
import rich.padding

# Own modules
import dds_cli
import dds_cli.utils
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
        authenticate: bool = True,
        no_prompt: bool = False,
        token_path: str = None,
    ):
        """Handle actions regarding data deletion in the cli."""
        # Initiate DDSBaseClass to authenticate user
        super().__init__(
            project=project,
            method=method,
            authenticate=authenticate,
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
                for non_ex_file in not_exists:
                    self.failed_files["Errors"].append({non_ex_file: f"No such {level.lower()}"})
                for failed_file, failure_info in delete_failed.items():
                    self.failed_files["Errors"].append({failed_file: failure_info})
            else:
                # Create table and add columns
                table = rich.table.Table(
                    title=f"{level}s not deleted",
                    title_justify="left",
                    show_header=True,
                    header_style="bold",
                )
                columns = [level, "Error"]
                for col in columns:
                    table.add_column(col)

                # Add rows
                for non_ex_file in not_exists:
                    table.add_row(rich.markup.escape(non_ex_file), f"No such {level.lower()}")

                for failed_file, failure_info in delete_failed.items():
                    table.add_row(
                        f"[light_salmon3]{rich.markup.escape(failed_file)}[/light_salmon3]",
                        f"[light_salmon3]{rich.markup.escape(failure_info)}[/light_salmon3]",
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
    def remove_all(self, *_, **__):
        """Remove all files in project."""
        # Perform request to API to perform deletion
        response_json, _ = dds_cli.utils.perform_request(
            DDSEndpoint.REMOVE_PROJ_CONT,
            method="delete",
            params={"project": self.project},
            headers=self.token,
            error_message="Failed to delete project contents",
        )

        # Print out response - deleted or not?
        queue_message: str = response_json.get("message")
        if "removed" not in response_json or "message" not in response_json:
            raise dds_cli.exceptions.APIError(
                "Malformatted response detected when attempting "
                f"to remove all files from {self.project}."
            )

        dds_cli.utils.console.print("\n" + queue_message)

    @removal_spinner
    def remove_file(self, files):
        """Remove specific files."""
        response_json, _ = dds_cli.utils.perform_request(
            DDSEndpoint.REMOVE_FILE,
            method="delete",
            params={"project": self.project},
            json=files,
            headers=self.token,
            error_message=f"Failed to delete file from project {self.project}",
        )

        # Get info in response
        self.__create_failed_table(resp_json=response_json)

    @removal_spinner
    def remove_folder(self, folder):
        """Remove specific folders."""
        response_json, _ = dds_cli.utils.perform_request(
            DDSEndpoint.REMOVE_FOLDER,
            method="delete",
            params={"project": self.project},
            json=folder,
            headers=self.token,
            error_message=f"Failed to delete folder(s) from project '{self.project}'",
        )

        self.__create_failed_table(resp_json=response_json, level="Folder")

        if response_json.get("nr_deleted"):
            LOG.info(
                "%s files were successfully deleted in %s.", response_json["nr_deleted"], folder
            )
        # Print extra warning if s3 deletion succeeded, db failed
        if response_json.get("fail_type") == "db":
            LOG.error(
                "Some files were deleted, but their database entries were not. "
                + "Try to run the command again, and contact Data Centre if the problem persists."
            )
