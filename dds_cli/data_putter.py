"""Data putter."""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import concurrent.futures
import itertools
import logging
import pathlib
import shutil

# Installed
import boto3
import botocore
import requests
from rich.progress import Progress, SpinnerColumn, BarColumn
import simplejson
import http

# Own modules
from dds_cli import base
from dds_cli import exceptions
from dds_cli import data_remover as dr
from dds_cli import DDSEndpoint
from dds_cli import file_encryptor as fe
from dds_cli import file_handler_local as fhl
from dds_cli import status
from dds_cli import text_handler as txt
from dds_cli.cli_decorators import verify_proceed, update_status, subpath_required
from dds_cli import s3_connector as s3

import dds_cli
import dds_cli.utils

###############################################################################
# START LOGGING CONFIG ################################# START LOGGING CONFIG #
###############################################################################

LOG = logging.getLogger(__name__)

###############################################################################
# MAIN FUNCTION ############################################### MAIN FUNCTION #
###############################################################################


def put(
    username,
    project,
    source,
    source_path_file,
    break_on_fail,
    overwrite,
    num_threads,
    silent,
    no_prompt,
):
    """Handle upload of data."""
    # Initialize delivery - check user access etc
    with DataPutter(
        username=username,
        project=project,
        source=source,
        source_path_file=source_path_file,
        break_on_fail=break_on_fail,
        overwrite=overwrite,
        silent=silent,
        no_prompt=no_prompt,
    ) as putter:

        # Progress object to keep track of progress tasks
        with Progress(
            "{task.description}",
            BarColumn(bar_width=None),
            " • ",
            "[progress.percentage]{task.percentage:>3.1f}%",
            refresh_per_second=2,
            console=dds_cli.utils.stderr_console,
        ) as progress:

            # Keep track of futures
            upload_threads = {}

            # Iterator to keep track of which files have been handled
            iterator = iter(putter.filehandler.data.copy())

            with concurrent.futures.ThreadPoolExecutor() as texec:
                # Start main progress bar - total uploaded files
                upload_task = progress.add_task(
                    description="Upload",
                    total=len(putter.filehandler.data),
                )

                # Schedule the first num_threads futures for upload
                for file in itertools.islice(iterator, num_threads):
                    LOG.debug(f"Starting: {file}")
                    upload_threads[
                        texec.submit(
                            putter.stage_and_upload,
                            file=file,
                            progress=progress,
                        )
                    ] = file

                try:
                    # Continue until all files are done
                    while upload_threads:
                        # Wait for the next future to complete, _ are the unfinished
                        done, _ = concurrent.futures.wait(
                            upload_threads,
                            return_when=concurrent.futures.FIRST_COMPLETED,
                        )

                        # Number of new upload tasks that can be started
                        new_tasks = 0

                        # Get result from future and schedule database update
                        for fut in done:
                            uploaded_file = upload_threads.pop(fut)
                            LOG.debug(f"Future done for file: {uploaded_file}")

                            # Get result
                            try:
                                file_uploaded = fut.result()
                                LOG.debug(f"Upload of {uploaded_file} successful: {file_uploaded}")
                            except concurrent.futures.BrokenExecutor as err:
                                LOG.error(f"Upload of file {uploaded_file} failed! Error: {err}")
                                continue

                            # Increase the main progress bar
                            progress.advance(upload_task)

                            # New available threads
                            new_tasks += 1

                        # Schedule the next set of futures for upload
                        for next_file in itertools.islice(iterator, new_tasks):
                            LOG.debug(f"Starting: {next_file}")
                            upload_threads[
                                texec.submit(
                                    putter.stage_and_upload,
                                    file=next_file,
                                    progress=progress,
                                )
                            ] = next_file
                except KeyboardInterrupt:
                    LOG.warning(
                        "KeyboardInterrupt found - shutting down delivery gracefully. "
                        "This will finish the ongoing uploads. If you want to force "
                        "shutdown, repeat `Ctrl+C`. This is not advised. "
                    )

                    # Flag for threads to find
                    putter.stop_doing = True

                    # Stop and remove main progress bar
                    progress.remove_task(upload_task)

                    # Stop all tasks that are not currently uploading
                    _ = [
                        progress.stop_task(x)
                        for x in [y.id for y in progress.tasks if y.fields.get("step") != "put"]
                    ]


###############################################################################
# CLASSES ########################################################### CLASSES #
###############################################################################


class DataPutter(base.DDSBaseClass):
    """Data putter class."""

    def __init__(
        self,
        username: str,
        project: str = None,
        break_on_fail: bool = False,
        overwrite: bool = False,
        source: tuple = (),
        source_path_file: pathlib.Path = None,
        silent: bool = False,
        method: str = "put",
        no_prompt: bool = False,
    ):
        """Handle actions regarding upload of data."""
        # Initiate DDSBaseClass to authenticate user
        super().__init__(username=username, project=project, method=method, no_prompt=no_prompt)

        # Initiate DataPutter specific attributes
        self.break_on_fail = break_on_fail
        self.overwrite = overwrite
        self.silent = silent
        self.filehandler = None

        # Only method "put" can use the DataPutter class
        if self.method != "put":
            raise dds_cli.exceptions.InvalidMethodError(
                attempted_method=self.method, message="DataPutter attempting unauthorized method."
            )

        # Get info required for put
        self.sensitive, public_key = self.__get_project_info()
        self.keys = (None, public_key)
        self.s3connector = self.__get_safespring_keys()

        # Start file prep progress
        with Progress(
            "[bold]{task.description}",
            SpinnerColumn(spinner_name="dots12", style="white"),
            console=dds_cli.utils.stderr_console,
        ) as progress:
            # Spinner while collecting file info
            wait_task = progress.add_task("Collecting and preparing data", step="prepare")

            # Get file info
            self.filehandler = fhl.LocalFileHandler(
                user_input=(source, source_path_file),
                project=self.project,
                temporary_destination=self.dds_directory.directories["FILES"],
            )

            # Check which, if any, files exist in the db
            files_in_db = self.filehandler.check_previous_upload(token=self.token)

            # Quit if error and flag
            if files_in_db and self.break_on_fail and not self.overwrite:
                raise exceptions.UploadError(
                    "Some files have already been uploaded (or have identical names to "
                    "previously uploaded files) and the '--break-on-fail' flag was used. "
                    "Try again with the '--overwrite' flag if you want to upload these files."
                )

            # Generate status dict
            self.status = self.filehandler.create_upload_status_dict(
                existing_files=files_in_db, overwrite=self.overwrite
            )

            # Remove spinner
            progress.remove_task(wait_task)

        if not self.filehandler.data:
            raise exceptions.UploadError("No data to upload.")

    # Private methods #################### Private methods #
    def __get_project_info(self):
        """ """
        try:
            response = requests.get(
                DDSEndpoint.PROJ_PUBLIC,
                params={"project": self.project},
                headers=self.token,
                timeout=DDSEndpoint.TIMEOUT,
            )
        except requests.exceptions.RequestException as err:
            LOG.fatal(str(err))
            raise exceptions.ApiRequestError(message=str(err))

        if not response.ok:
            message = "Failed getting required project information from API."
            if response.status_code == http.HTTPStatus.INTERNAL_SERVER_ERROR:
                raise exceptions.ApiResponseError(message=f"{message}: {response.reason}")

            raise exceptions.DDSCLIException(message=f"{message}: {response.json().get('message')}")

        response_json = dds_cli.utils.get_json_response(response=response)
        if "sensitive" not in response_json:
            raise exceptions.ApiResponseError(
                message="No information regarding project sensitivity."
            )
        sensitive = response_json.get("sensitive")
        public = response_json.get("public")
        if sensitive and not public:
            raise exceptions.ApiResponseError(
                "Public project key required to deliver data within sensitive projects."
            )

        return sensitive, public

    def __get_safespring_keys(self):
        """Get safespring keys."""
        return s3.S3Connector(project_id=self.project, token=self.token)

    # Public methods ###################### Public methods #
    def stage_nonsensitive(self, file, progress, task):
        file_info = self.filehandler.data[file]
        # Perform staging
        try:
            if file_info["compressed"]:  # TODO: or no_compression
                # TODO: Add spinner?
                # Copy file and presever metadata
                shutil.copy2(src=file_info["path_raw"], dst=file_info["path_processed"])
            else:
                # Progress bar for processing
                progress.reset(
                    task,
                    description=txt.TextHandler.task_name(file=file, step="stage"),
                    total=file_info["size_raw"],
                    visible=not self.silent,
                )
                streamed_chunks = self.filehandler.stream_compressed_data(file=file)
                self.filehandler.save_streamed_chunks(
                    chunks=streamed_chunks,
                    outfile=file_info["path_processed"],
                    progress=(progress, task),
                )
                self.filehandler.data[file]["size_processed"] = (
                    file_info["path_processed"].stat().st_size
                )
        except (OSError, TypeError, FileExistsError) as err:
            LOG.warning(err)
            raise exceptions.StagingError(err)

    def stage_sensitive(self, file, progress, task):
        file_info = self.filehandler.data[file]
        # Perform compression/encryption
        try:
            if file_info["compressed"]:  # TODO: or no_compression
                # TODO: Add spinner?
                streamed_chunks = self.filehandler.stream_raw_data(file=file)
            else:
                streamed_chunks = self.filehandler.stream_compressed_data(file=file)

            # Stream the chunks into the encryptor to save the encrypted chunks
            with fe.Encryptor(project_keys=self.keys) as encryptor:

                # Encrypt and save chunks
                encryptor.encrypt_filechunks(
                    chunks=streamed_chunks,
                    outfile=file_info["path_processed"],
                    progress=(progress, task),
                )

                # Get hex version of public key -- saved in db
                file_public_key = encryptor.get_public_component_hex(
                    private_key=encryptor.my_private
                )
                salt = encryptor.salt

                # Update file info incl size, public key, salt
                self.filehandler.data[file]["public_key"] = file_public_key
                self.filehandler.data[file]["salt"] = salt
                self.filehandler.data[file]["size_processed"] = (
                    file_info["path_processed"].stat().st_size
                )
        except (
            OSError,
            TypeError,
            FileExistsError,
            InterruptedError,
        ) as err:  # TODO: Check which exceptions
            LOG.exception(err)
            raise exceptions.ProcessingError(err)

        LOG.debug(
            f"File successfully encrypted: {file}. New location: {file_info['path_processed']}"
        )

    @verify_proceed
    @subpath_required
    def stage_and_upload(self, file, progress, task):
        """Prepare data and perform upload."""
        # Info on current file
        file_info = self.filehandler.data[file]

        # Handle non-sensitive project data
        if self.sensitive:
            self.stage_sensitive(file=file, progress=progress, task=task)

            # Progress bar for processing
            progress.reset(
                task,
                description=txt.TextHandler.task_name(file=file, step="encrypt"),
                total=file_info["size_raw"],
                visible=not self.silent,
            )
        else:
            self.stage_nonsensitive(file=file, progress=progress, task=task)

            # Update progress bar for upload
            progress.reset(
                task,
                description=txt.TextHandler.task_name(file=file, step="put"),
                total=self.filehandler.data[file].get(
                    "size_processed", self.filehandler.data[file].get("size_raw")
                ),
                step="put",
            )

        # Perform upload
        try:
            self.put(file=file, progress=progress, task=task)
        except (
            botocore.client.ClientError,
            boto3.exceptions.Boto3Error,
            botocore.exceptions.BotoCoreError,
            FileNotFoundError,
            TypeError,
        ) as err:
            LOG.exception(err)
            raise exceptions.UploadError(err)

        # Perform database update
        try:
            self.add_file_db(file=file)
        except (exceptions.DatabaseUpdateError, exceptions.StatusError) as err:
            LOG.exception(err)
            raise

        LOG.info(f"File successfully uploaded and added to the database: {file}")

        # Delete temporary processed file locally
        dr.DataRemover.delete_tempfile(file=file_info["path_processed"])

    @update_status
    def put(self, file, progress, task):
        """Upload files to the cloud."""
        # File info
        file_local = str(self.filehandler.data[file]["path_processed"])
        file_remote = self.filehandler.data[file]["path_remote"]

        with self.s3connector as conn:
            # Upload file
            conn.resource.meta.client.upload_file(
                Filename=file_local,
                Bucket=conn.bucketname,
                Key=file_remote,
                ExtraArgs={
                    "ACL": "private",  # Access control list
                    "CacheControl": "no-store",  # Don't store cache
                },
                Callback=status.ProgressPercentage(
                    progress=progress,
                    task=task,
                )
                if task is not None
                else None,
            )

    @update_status
    def add_file_db(self, file):
        """Make API request to add file to DB."""
        # Get file info and specify info required in db
        fileinfo = self.filehandler.data[file]

        # Request params
        params = {"project": self.project}
        file_info = {
            "name": file,
            "name_in_bucket": str(fileinfo["path_remote"]),
            "subpath": str(fileinfo["subpath"]),
            "size": fileinfo["size_raw"],
            "size_processed": fileinfo.get("size_processed"),
            "compressed": not fileinfo["compressed"],
            "salt": fileinfo.get("salt"),
            "public_key": fileinfo.get("public_key"),
            "checksum": fileinfo["checksum"],
        }

        # Send file info to API - post if new file, put if overwrite
        put_or_post = requests.put if fileinfo["overwrite"] else requests.post
        try:
            response = put_or_post(
                DDSEndpoint.FILE_NEW,
                params=params,
                json=file_info,
                headers=self.token,
                timeout=DDSEndpoint.TIMEOUT,
            )
        except requests.exceptions.RequestException as err:
            raise exceptions.DatabaseUpdateError(err)

        # Error if failed
        if not response.ok:
            raise exceptions.DatabaseUpdateError(
                f"Failed to add file '{file}' to database: {response.text}"
            )
