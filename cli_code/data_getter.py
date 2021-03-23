"""Data getter."""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import logging
import pathlib
import traceback
import sys
import os

# Installed
import rich
from rich.progress import Progress
import botocore
import requests

# Own modules
from cli_code import DDSEndpoint
from cli_code import base
from cli_code import file_handler_remote as fhr
from cli_code import s3_connector as s3
from cli_code.cli_decorators import verify_proceed, update_status, subpath_required
from cli_code import status

###############################################################################
# START LOGGING CONFIG ################################# START LOGGING CONFIG #
###############################################################################

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)

###############################################################################
# RICH CONFIG ################################################### RICH CONFIG #
###############################################################################

console = rich.console.Console()

###############################################################################
# CLASSES ########################################################### CLASSES #
###############################################################################


class DataGetter(base.DDSBaseClass):
    """Data getter class."""

    def __init__(
        self,
        username: str = None,
        config: pathlib.Path = None,
        project: str = None,
        break_on_fail: bool = False,
        get_all: bool = False,
        source: tuple = (),
        source_path_file: pathlib.Path = None,
        destination: pathlib.Path = pathlib.Path(""),
    ):

        # Initiate DDSBaseClass to authenticate user
        super().__init__(username=username, config=config, project=project)

        # Initiate DataGetter specific attributes
        self.break_on_fail = break_on_fail
        self.filehandler = None
        self.status = dict()

        # Only method "get" can use the DataGetter class
        if self.method != "get":
            console.print(
                f"\n:no_entry_sign: Unauthorized method: {self.method} :no_entry_sign:\n"
            )
            os._exit(os.EX_OK)

        self.filehandler = fhr.RemoteFileHandler(
            get_all=get_all,
            user_input=(source, source_path_file),
            token=self.token,
            destination=destination,
        )

        if self.filehandler.failed and self.break_on_fail:
            console.print(
                "\n:warning: Some specified files were not found in the system "
                "and '--break-on-fail' flag used. :warning:\n\n"
                f"Files not found: {self.filehandler.failed}\n"
            )
            os._exit(os.EX_OK)

        if not self.filehandler.data:
            console.print("\nNo files to download.\n")
            os._exit(os.EX_OK)

        self.status = self.filehandler.create_download_status_dict()
        self.progress = Progress()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if exc_type is not None:
            traceback.print_exception(exc_type, exc_value, tb)
            return False  # uncomment to pass exception through

        return True

    @verify_proceed
    @update_status
    @subpath_required
    def get(self, file, progress, task):
        """Downloads files from the cloud."""

        downloaded = False
        error = ""
        file_local = str(file)
        file_remote = self.filehandler.data[file]["name_in_bucket"]

        with s3.S3Connector(project_id=self.project, token=self.token) as conn:

            if None in [conn.url, conn.keys, conn.bucketname]:
                error = "No s3 info returned! " + conn.message
            else:
                # Upload file
                try:
                    conn.resource.meta.client.download_file(
                        Filename=file_local,
                        Bucket=conn.bucketname,
                        Key=file_remote,
                        Callback=status.ProgressPercentage(
                            progress=progress, task=task
                        ),
                    )
                except botocore.client.ClientError as err:
                    error = f"S3 download of file '{file}' failed: {err}"
                    LOG.exception("%s: %s", file, err)
                else:
                    downloaded = True

        return downloaded, error

    @verify_proceed
    @update_status
    def update_db(self, file):
        """Update file info in db."""

        updated_in_db = False
        error = ""

        # Get file info
        fileinfo = self.filehandler.data[file]
        params = {"name": fileinfo["name_in_db"]}

        # Send file info to API
        response = requests.put(
            DDSEndpoint.FILE_UPDATE, params=params, headers=self.token
        )

        # Error if failed
        if not response.ok:
            error = f"Failed to update file '{file}' in db: {response.text}"
            LOG.exception(error)
            return updated_in_db, error

        updated_in_db, error = (True, response.json()["message"])
        return updated_in_db, error