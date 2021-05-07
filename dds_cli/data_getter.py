"""Data getter."""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import logging
import os
import pathlib
import sys
import traceback

# Installed
import boto3
import botocore
import rich
import requests
import simplejson
from rich.progress import Progress, SpinnerColumn

# Own modules
from dds_cli import base
from dds_cli import DDSEndpoint, FileSegment
from dds_cli import file_handler_remote as fhr
from dds_cli import data_remover as dr
from dds_cli import file_compressor as fc
from dds_cli import file_encryptor as fe
from dds_cli import s3_connector as s3
from dds_cli import status
from dds_cli import text_handler as txt
from dds_cli.cli_decorators import verify_proceed, update_status, subpath_required

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
        silent: bool = False,
        verify_checksum: bool = False,
    ):

        # Initiate DDSBaseClass to authenticate user
        super().__init__(
            username=username, config=config, project=project, log_location=destination["LOGS"]
        )

        # Initiate DataGetter specific attributes
        self.break_on_fail = break_on_fail
        self.verify_checksum = verify_checksum
        self.silent = silent
        self.filehandler = None
        # self.log_location = destination["LOGS"]

        # Only method "get" can use the DataGetter class
        if self.method != "get":
            console.print(f"\n:no_entry_sign: Unauthorized method: {self.method} :no_entry_sign:\n")
            os._exit(0)

        # Start file prep progress
        with Progress(
            "[bold]{task.description}",
            SpinnerColumn(spinner_name="dots12", style="white"),
        ) as progress:
            wait_task = progress.add_task("Collecting and preparing data", step="prepare")
            self.filehandler = fhr.RemoteFileHandler(
                get_all=get_all,
                user_input=(source, source_path_file),
                token=self.token,
                destination=destination["FILES"],
            )

            if self.filehandler.failed and self.break_on_fail:
                console.print(
                    "\n:warning: Some specified files were not found in the system "
                    "and '--break-on-fail' flag used. :warning:\n\n"
                    f"Files not found: {self.filehandler.failed}\n"
                )
                os._exit(0)

            if not self.filehandler.data:
                console.print("\nNo files to download.\n")
                os._exit(0)

            self.status = self.filehandler.create_download_status_dict()

            progress.remove_task(wait_task)

    # Public methods ############ Public methods #
    @verify_proceed
    @subpath_required
    def download_and_verify(self, file, progress):
        """Downloads the file, reveals the original data and verifies the integrity."""

        all_ok, message = (False, "")
        file_info = self.filehandler.data[file]

        # File task for downloading
        task = progress.add_task(
            description=txt.TextHandler.task_name(file=file, step="get"),
            total=file_info["size_encrypted"],
            visible=not self.silent,
        )

        # Perform download
        file_downloaded, message = self.get(file=file, progress=progress, task=task)

        # Update progress task for decryption
        progress.reset(
            task,
            description=txt.TextHandler.task_name(file=file, step="decrypt"),
            total=file_info["size"],
        )

        LOG.debug("File %s downloaded: %s", file, file_downloaded)

        if file_downloaded:
            db_updated, message = self.update_db(file=file)
            LOG.debug("Database updated: %s", db_updated)

            LOG.info("Beginning decryption of file %s...", file)
            file_saved = False
            with fe.Decryptor(
                project_keys=self.keys,
                peer_public=file_info["public_key"],
                key_salt=file_info["key_salt"],
            ) as decryptor:

                streamed_chunks = decryptor.decrypt_file(infile=file_info["path_downloaded"])

                stream_to_file_func = (
                    fc.Compressor.decompress_filechunks
                    if file_info["compressed"]
                    else self.filehandler.write_file
                )

                file_saved, message = stream_to_file_func(
                    chunks=streamed_chunks,
                    outfile=file,
                )

            LOG.debug("file saved? %s", file_saved)
            if file_saved:
                # TODO (ina): decide on checksum verification method --
                # this checks original, the other is generated from compressed
                all_ok, message = (
                    fe.Encryptor.verify_checksum(file=file, correct_checksum=file_info["checksum"])
                    if self.verify_checksum
                    else (True, "")
                )

            dr.DataRemover.delete_tempfile(file=file_info["path_downloaded"])

        progress.remove_task(task)
        return all_ok, message

    @update_status
    def get(self, file, progress, task):
        """Downloads files from the cloud."""

        downloaded = False
        error = ""
        file_local = str(self.filehandler.data[file]["path_downloaded"])
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
                        Callback=status.ProgressPercentage(progress=progress, task=task)
                        if not self.silent
                        else None,
                    )
                except (
                    botocore.client.ClientError,
                    boto3.exceptions.Boto3Error,
                ) as err:
                    error = f"S3 download of file '{file}' failed: {err}"
                    LOG.exception("%s: %s", file, err)
                else:
                    downloaded = True

        return downloaded, error

    @update_status
    def update_db(self, file):
        """Update file info in db."""

        updated_in_db = False
        error = ""

        # Get file info
        fileinfo = self.filehandler.data[file]
        params = {"name": fileinfo["name_in_db"]}

        # Send file info to API
        try:
            response = requests.put(DDSEndpoint.FILE_UPDATE, params=params, headers=self.token)
        except requests.exceptions.RequestException as err:
            raise SystemExit from err

        # Error if failed
        if not response.ok:
            error = f"Failed to update file '{file}' in db: {response.text}"
            LOG.exception(error)
            return updated_in_db, error

        try:
            updated_in_db, error = (True, response.json()["message"])
        except simplejson.JSONDecodeError as err:
            raise SystemExit from err

        return updated_in_db, error
