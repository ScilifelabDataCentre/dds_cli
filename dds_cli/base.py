"""Base class for the DDS CLI. Verifies the user's access to the DDS."""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import logging
import pathlib
import typing

# Installed
from rich.progress import Progress, SpinnerColumn

# Own modules
import dds_cli.directory
import dds_cli.timestamp
import dds_cli.utils

from dds_cli import (
    DDS_KEYS_REQUIRED_METHODS,
)
from dds_cli import DDSEndpoint
from dds_cli import s3_connector as s3
from dds_cli import user
from dds_cli import exceptions

###############################################################################
# START LOGGING CONFIG ################################# START LOGGING CONFIG #
###############################################################################

LOG = logging.getLogger(__name__)


###############################################################################
# CLASSES ########################################################### CLASSES #
###############################################################################


class DDSBaseClass:
    """Data Delivery System base class. For common operations."""

    def __init__(
        self,
        project=None,
        method: str = None,
        authenticate: bool = True,
        force_renew_token: bool = False,
        totp: str = None,
        no_prompt: bool = False,
        token_path: str = None,
        allow_group: bool = False,
        staging_dir: dds_cli.directory.DDSDirectory = None,
    ):
        """Initialize Base class for authenticating the user and preparing for DDS action."""
        self.project = project
        self.method = method
        self.no_prompt = no_prompt
        self.token_path = token_path

        self.totp = totp

        # Keyboardinterrupt
        self.stop_doing = False

        # Authenticate the user and get the token
        if authenticate:
            dds_user = user.User(
                force_renew_token=force_renew_token,
                no_prompt=no_prompt,
                token_path=token_path,
                allow_group=allow_group,
                totp=totp,
            )
            self.token = dds_user.token_dict

        # Project access only required if trying to upload, download or list
        # files within project
        # TODO: Move to DataPutter / DataGetter??
        if self.method in DDS_KEYS_REQUIRED_METHODS:
            # NOTE: Might be something to refactor in the future, but needed for now
            self.dds_directory = staging_dir
            self.temporary_directory = self.dds_directory.directories["ROOT"]
            self.failed_delivery_log = self.dds_directory.directories["LOGS"] / pathlib.Path(
                "dds_failed_delivery.json"
            )

            if self.method == "put":
                self.s3connector = self.__get_safespring_keys()

            self.keys = self.__get_project_keys()

            self.status: typing.Dict = {}
            self.filehandler = None

    def __enter__(self):
        """Return self when using context manager."""
        return self

    def __exit__(self, exception_type, exception_value, traceback, max_fileerrs: int = 40):
        """Finish and print out delivery summary.

        This is not entered if there's an error during __init__.
        """
        if self.method in ["put", "get", "rm"]:
            if self.method != "rm":
                self.__printout_delivery_summary()

        # Exception is not handled
        if exception_type is not None:
            LOG.debug("Exception: %s with value %s", exception_type, exception_value)
            return False

        return True

    # Public methods ############################### Public methods #

    def set_token(self, token_dict: dict) -> None:
        """Sets the token for the base class.
        Called from auth class to set the token when authenticating
        in the gui without running the base class with authenticate set to true.
        """
        self.token = token_dict

    def get_project_info(self):
        """Collect project information from API."""

        # Get info about a project from API
        response, _ = dds_cli.utils.perform_request(
            DDSEndpoint.PROJ_INFO,
            method="get",
            headers=self.token,
            params={"project": self.project},
            error_message="Failed to get project information",
        )

        project_info = response.get("project_info")

        # If not project info was retrieved from the request, throw an exception
        if not project_info:
            raise dds_cli.exceptions.ApiResponseError(message="No project information to display.")

        return project_info

    def generate_project_table(self, project_info):
        """Generate a table from some project info provided"""

        # Print project info table
        table = dds_cli.utils.create_table(
            title="Project information.",
            columns=["Project ID", "Created by", "Status", "Last updated", "Size"],
            rows=[
                project_info,
            ],
            caption=f"Information about project {project_info['Project ID']}",
        )

        return table

    # Private methods ############################### Private methods #
    def __get_safespring_keys(self):
        """Get safespring keys."""
        return s3.S3Connector(project_id=self.project, token=self.token)

    def __get_project_keys(self):
        """Get public and private project keys depending on method."""
        # Project public key required for both put and get
        public = self.__get_key()

        # Project private only required for get
        private = None
        if self.method == "get":
            # Key derivation on server is slow - display spinner
            information_to_user = "Preparing for download. This may be slow. Please wait..."
            with Progress(
                SpinnerColumn(spinner_name="dots12", style="blue"),
                "{task.description}",
                console=dds_cli.utils.stderr_console,
            ) as spinner:
                # Start spinner
                task = spinner.add_task(description=information_to_user)
                try:
                    # Get key
                    private = self.__get_key(private=True)
                finally:
                    # Always remove spinner
                    spinner.remove_task(task)

        return private, public

    def __get_key(self, private: bool = False):
        """Get public key for project."""
        key_type = "private" if private else "public"
        # Get key from API
        project_public, _ = dds_cli.utils.perform_request(
            DDSEndpoint.PROJ_PRIVATE if private else DDSEndpoint.PROJ_PUBLIC,
            method="get",
            params={"project": self.project},
            headers=self.token,
            error_message="Failed to get project key",
        )

        if key_type not in project_public:
            raise exceptions.NoKeyError(f"Project access denied: No {key_type} key.")

        return project_public[key_type]

    def __printout_delivery_summary(self):
        """Print out the delivery summary if any files were cancelled."""
        if self.stop_doing:
            LOG.info("%s cancelled.\n", "Upload" if self.method == "put" else "Download")
            return

        # TODO: Look into a better summary print out - old deleted for now
        any_failed = self.__collect_all_failed()
        true_failed = [entry for entry in any_failed if entry["message"] != "File already uploaded"]
        nr_uploaded = len(any_failed) - len(true_failed)

        # Clear dict to not take up too much space
        self.filehandler.failed.clear()

        if true_failed:
            log_file_info: str = (
                "When contacting DDS support, please attach the log file(s) located in "
                f"{self.dds_directory.directories['LOGS']} to the ticket. "
                "If you used the '--log-file' option when running your command, "
                "please also attach that file.\n"
                "[red][bold]Do not[/bold][/red] delete these files."
            )
            if self.method == "put":
                # Raise exception in order to give exit code 1
                raise exceptions.UploadError(
                    "Errors occurred during upload.\n"
                    "If you wish to retry the upload, re-run the 'dds data put' command again, "
                    "specifying the same options as you did now. To also overwrite the files "
                    "that were uploaded, also add the '--overwrite' flag at the end of the command.\n\n"
                    f"{log_file_info}"
                )

            # TODO: --destination should be able to >at least< overwrite the files in the
            # previously created download location.
            raise exceptions.DownloadError(
                "Errors occurred during download.\n"
                "If you wish to retry the download, re-run the `dds data get` command again, "
                "specifying the same options as you did now. A new directory will "
                "automatically be created and all files will be downloaded again.\n\n"
                f"{log_file_info}"
            )

        if nr_uploaded:
            # Raise exception in order to give exit code 1
            LOG.warning(
                "%s files have already been uploaded to this project.\n"
                "Upload [bold]partially[/bold] completed!\n",
                nr_uploaded,
            )

        else:
            # Printout if no cancelled/failed files
            dds_cli.utils.console.print(
                f"\n{'Upload' if self.method == 'put' else 'Download'} completed!\n"
            )

        if self.method == "get" and len(self.filehandler.data) > len(any_failed):
            LOG.info("Any downloaded files are located at: %s.", self.filehandler.local_destination)

    def __collect_all_failed(self, sort: bool = True) -> list:
        """Put cancelled files from status in to failed dict and sort the output."""
        # Transform all items to string
        self.filehandler.data = {
            str(file): {str(x): str(y) for x, y in info.items()}
            for file, info in list(self.filehandler.data.items())
        }
        self.status = {
            str(file): {str(x): str(y) for x, y in info.items()}
            for file, info in list(self.status.items())
        }

        # Get cancelled files
        self.filehandler.failed.update(
            {
                file: {
                    **info,
                    "message": self.status[file]["message"],
                    "failed_op": self.status[file]["failed_op"],
                }
                for file, info in self.filehandler.data.items()
                if self.status[file]["cancel"] in [True, "True"]
            }
        )

        # Sort by which directory the files are in
        out_data = self.filehandler.failed
        out_data = [{"filepath": entry[0], **entry[1]} for entry in self.filehandler.failed.items()]
        if sort:
            out_data.sort(key=lambda x: x["filepath"])

        return out_data
