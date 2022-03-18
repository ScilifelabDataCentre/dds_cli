"""Base class for the DDS CLI. Verifies the users access to the DDS."""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import logging
import os
import pathlib

# Installed
import http
import requests
import simplejson

# Own modules
import dds_cli.directory
import dds_cli.timestamp

from dds_cli import (
    DDS_METHODS,
    DDS_DIR_REQUIRED_METHODS,
    DDS_KEYS_REQUIRED_METHODS,
)
from dds_cli import DDSEndpoint
from dds_cli import s3_connector as s3
from dds_cli import user
from dds_cli import exceptions
from dds_cli import utils

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
        dds_directory: pathlib.Path = None,
        mount_dir: pathlib.Path = None,
        method: str = None,
        authenticate: bool = True,
        method_check: bool = True,
        force_renew_token: bool = False,
        no_prompt: bool = False,
        token_path: str = None,
    ):
        """Initialize Base class for authenticating the user and preparing for DDS action."""
        self.project = project
        self.method_check = method_check
        self.method = method
        self.no_prompt = no_prompt
        self.token_path = token_path

        if self.method_check:
            # Get attempted operation e.g. put/ls/rm/get
            if self.method not in DDS_METHODS:
                raise exceptions.InvalidMethodError(attempted_method=self.method)
            LOG.debug(f"Attempted operation: {self.method}")

            # Use user defined destination if any specified
            if self.method in DDS_DIR_REQUIRED_METHODS:
                default_dir = pathlib.Path(
                    f"DataDelivery_{dds_cli.timestamp.TimeStamp().timestamp}"
                )
                if mount_dir:
                    new_directory = mount_dir / default_dir
                elif dds_directory:
                    new_directory = dds_directory
                else:
                    new_directory = pathlib.Path.cwd() / default_dir

                self.temporary_directory = new_directory

                self.dds_directory = dds_cli.directory.DDSDirectory(path=new_directory)
                self.failed_delivery_log = self.dds_directory.directories["LOGS"] / pathlib.Path(
                    "dds_failed_delivery.txt"
                )

        # Keyboardinterrupt
        self.stop_doing = False

        # Authenticate the user and get the token
        if authenticate:
            dds_user = user.User(
                force_renew_token=force_renew_token,
                no_prompt=no_prompt,
                token_path=token_path,
            )
            self.token = dds_user.token_dict

        # Project access only required if trying to upload, download or list
        # files within project
        if self.method in DDS_KEYS_REQUIRED_METHODS:
            if self.method == "put":
                self.s3connector = self.__get_safespring_keys()

            self.keys = self.__get_project_keys()

            self.status = dict()
            self.filehandler = None

    def __enter__(self):
        """Return self when using context manager."""
        return self

    def __exit__(self, exc_type, exc_value, tb, max_fileerrs: int = 40):
        """Finish and print out delivery summary."""
        if self.method in ["put", "get"]:
            self.__printout_delivery_summary()

        # Exception is not handled
        if exc_type is not None:
            LOG.debug(f"Exception: {exc_type} with value {exc_value}")
            return False

        return True

    # Private methods ############################### Private methods #
    def __get_safespring_keys(self):
        """Get safespring keys."""
        return s3.S3Connector(project_id=self.project, token=self.token)

    def __get_project_keys(self):
        """Get public and private project keys depending on method."""
        # Project public key required for both put and get
        public = self.__get_key()

        # Project private only required for get
        private = self.__get_key(private=True) if self.method == "get" else None

        return private, public

    def __get_key(self, private: bool = False):
        """Get public key for project."""
        key_type = "private" if private else "public"
        # Get key from API
        try:
            response = requests.get(
                DDSEndpoint.PROJ_PRIVATE if private else DDSEndpoint.PROJ_PUBLIC,
                params={"project": self.project},
                headers=self.token,
                timeout=DDSEndpoint.TIMEOUT,
            )
        except requests.exceptions.RequestException as err:
            LOG.fatal(str(err))
            raise SystemExit from err

        if not response.ok:
            message = "Failed getting key from DDS API"
            if response.status_code == http.HTTPStatus.INTERNAL_SERVER_ERROR:
                raise exceptions.ApiResponseError(message=f"{message}: {response.reason}")

            raise exceptions.DDSCLIException(message=f"{message}: {response.json().get('message')}")

        # Get key from response
        try:
            project_public = response.json()
        except simplejson.JSONDecodeError as err:
            LOG.fatal(str(err))
            raise SystemExit from err

        if key_type not in project_public:
            utils.console.print(
                "\n:no_entry_sign: Project access denied: No {key_type} key. :no_entry_sign:\n"
            )
            os._exit(1)

        return project_public[key_type]

    def __printout_delivery_summary(self):
        """Print out the delivery summary if any files were cancelled."""
        # TODO: Look into a better summary print out - old deleted for now
        any_failed = self.__collect_all_failed()
        true_failed = [entry for entry in any_failed if entry["message"] != "File already uploaded"]
        nr_uploaded = len(any_failed) - len(true_failed)

        # Clear dict to not take up too much space
        self.filehandler.failed.clear()

        if true_failed:
            intro_error_message = (
                f"Errors occurred during {'upload' if self.method == 'put' else 'download'}"
            )

            if self.method == "put":
                retry_message = (
                    "If you wish to retry the upload, re-run the `dds data put` command again, "
                    "specifying the same options as you did now. To also overwrite the files "
                    "that were uploaded, also add the `--overwrite` flag at the end of the command."
                )
            else:
                # TODO: --destination should be able to >at least< overwrite the files in the
                # previously created download location.
                retry_message = (
                    "If you wish to retry the download, re-run the `dds data get` command again, "
                    "specifying the same options as you did now. A new directory will "
                    "automatically be created and all files will be downloaded again."
                )

            utils.stderr_console.print(
                f"{intro_error_message}. \n"
                f"{retry_message} \n\n"
                f"See {self.failed_delivery_log} for more information."
            )

        elif nr_uploaded:
            dds_cli.utils.console.print(
                (f"\nUpload completed!\n{nr_uploaded} files were already uploaded.\n")
            )

        else:
            # Printout if no cancelled/failed files
            dds_cli.utils.console.print(
                f"\n{'Upload' if self.method == 'put' else 'Download'} completed!\n"
            )

        if self.method == "get" and len(self.filehandler.data) > len(any_failed):
            LOG.info(f"Any downloaded files are located: {self.filehandler.local_destination}.")

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

        LOG.debug(self.filehandler.failed)

        # Sort by which directory the files are in
        out_data = self.filehandler.failed
        out_data = [{"filepath": entry[0], **entry[1]} for entry in self.filehandler.failed.items()]
        if sort:
            out_data.sort(key=lambda x: x["filepath"])

        return out_data
