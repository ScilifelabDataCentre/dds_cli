"""Data putter."""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import concurrent.futures
import itertools
import logging
import pathlib

# Installed
import boto3
import botocore
import requests
from rich.markup import escape
from rich.progress import Progress, SpinnerColumn, BarColumn
import simplejson

# Own modules
from dds_cli import base
from dds_cli import exceptions
from dds_cli import data_remover as dr
from dds_cli import DDSEndpoint
from dds_cli import file_encryptor as fe
from dds_cli import file_handler_local as fhl
from dds_cli import status
from dds_cli import text_handler as txt
from dds_cli.custom_decorators import verify_proceed, update_status, subpath_required

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
    mount_dir,
    project,
    source,
    source_path_file,
    break_on_fail,
    overwrite,
    num_threads,
    silent,
    no_prompt,
    token_path,
):
    """Handle upload of data."""
    # Initialize delivery - check user access etc
    with DataPutter(
        mount_dir=mount_dir,
        project=project,
        source=source,
        source_path_file=source_path_file,
        break_on_fail=break_on_fail,
        overwrite=overwrite,
        silent=silent,
        no_prompt=no_prompt,
        token_path=token_path,
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
                    LOG.debug(f"Starting: {escape(file)}")
                    upload_threads[
                        texec.submit(
                            putter.protect_and_upload,
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
                            LOG.debug(f"Future done for file: {escape(uploaded_file)}")

                            # Get result
                            try:
                                file_uploaded = fut.result()
                                LOG.debug(
                                    f"Upload of {escape(str(uploaded_file))} successful: {file_uploaded}"
                                )
                            except concurrent.futures.BrokenExecutor as err:
                                LOG.error(
                                    f"Upload of file {escape(uploaded_file)} failed! Error: {err}"
                                )
                                continue

                            # Increase the main progress bar
                            progress.advance(upload_task)

                            # New available threads
                            new_tasks += 1

                        # Schedule the next set of futures for upload
                        for next_file in itertools.islice(iterator, new_tasks):
                            LOG.debug(f"Starting: {escape(next_file)}")
                            upload_threads[
                                texec.submit(
                                    putter.protect_and_upload,
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
        project: str = None,
        mount_dir: pathlib.Path = None,
        break_on_fail: bool = False,
        overwrite: bool = False,
        source: tuple = (),
        source_path_file: pathlib.Path = None,
        silent: bool = False,
        method: str = "put",
        no_prompt: bool = False,
        token_path: str = None,
    ):
        """Handle actions regarding upload of data."""
        # Initiate DDSBaseClass to authenticate user
        super().__init__(
            project=project,
            mount_dir=mount_dir,
            method=method,
            no_prompt=no_prompt,
            token_path=token_path,
        )

        # Initiate DataPutter specific attributes
        self.break_on_fail = break_on_fail
        self.overwrite = overwrite
        self.silent = silent
        self.filehandler = None

        # Only method "put" can use the DataPutter class
        if self.method != "put":
            raise exceptions.AuthenticationError(f"Unauthorized method: '{self.method}'")

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

            # Verify that the Safespring S3 bucket exists
            # self.verify_bucket_exist()

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
            if self.temporary_folder and self.temporary_folder.is_dir():
                LOG.debug(f"Deleting temporary folder {self.temporary_folder}.")
                dds_utils.delete_folder(self.temporary_folder)
            raise exceptions.UploadError("No data to upload.")

    # Public methods ###################### Public methods #
    @verify_proceed
    @subpath_required
    def protect_and_upload(self, file, progress):
        """Process and upload the file while handling the progress bars."""
        # Variables
        all_ok, saved, message = (False, False, "")  # Error catching
        file_info = self.filehandler.data[file]  # Info on current file
        file_public_key, salt = ("", "")  # Crypto info

        # Progress bar for processing
        task = progress.add_task(
            description=txt.TextHandler.task_name(file=escape(file), step="encrypt"),
            total=file_info["size_raw"],
            visible=not self.silent,
        )

        # Stream chunks from file
        streamed_chunks = self.filehandler.stream_from_file(file=file)

        # Stream the chunks into the encryptor to save the encrypted chunks
        with fe.Encryptor(project_keys=self.keys) as encryptor:

            # Encrypt and save chunks
            saved, message = encryptor.encrypt_filechunks(
                chunks=streamed_chunks,
                outfile=file_info["path_processed"],
                progress=(progress, task),
            )

            # Get hex version of public key -- saved in db
            file_public_key = encryptor.get_public_component_hex(private_key=encryptor.my_private)
            salt = encryptor.salt

        LOG.debug(f"Updating file processed size: {file_info['path_processed']}")

        # Update file info incl size, public key, salt
        self.filehandler.data[file]["public_key"] = file_public_key
        self.filehandler.data[file]["salt"] = salt
        self.filehandler.data[file]["size_processed"] = file_info["path_processed"].stat().st_size

        if saved:
            LOG.debug(
                f"File successfully encrypted: {escape(file)}. New location: {escape(str(file_info['path_processed']))}"
            )
            # Update progress bar for upload
            progress.reset(
                task,
                description=txt.TextHandler.task_name(file=escape(file), step="put"),
                total=self.filehandler.data[file]["size_processed"],
                step="put",
            )

            # Perform upload
            file_uploaded, message = self.put(file=file, progress=progress, task=task)

            # Perform db update
            if file_uploaded:
                db_updated, message = self.add_file_db(file=file)

                if db_updated:
                    all_ok = True
                    LOG.debug(
                        f"File successfully uploaded and added to the database: {escape(file)}"
                    )

        if not saved or all_ok:
            # Delete temporary processed file locally
            LOG.debug(
                f"Deleting file {escape(str(file_info['path_processed']))} - "
                f"exists: {file_info['path_processed'].exists()}"
            )
            dr.DataRemover.delete_tempfile(file=file_info["path_processed"])

        # Remove progress bar task
        progress.remove_task(task)

        return all_ok, message

    @update_status
    def put(self, file, progress, task):
        """Upload files to the cloud."""
        # Variables
        uploaded = False
        error = ""

        # File info
        file_local = str(self.filehandler.data[file]["path_processed"])
        file_remote = self.filehandler.data[file]["path_remote"]

        try:
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
        except (
            botocore.client.ClientError,
            boto3.exceptions.Boto3Error,
            botocore.exceptions.BotoCoreError,
            FileNotFoundError,
            TypeError,
        ) as err:
            error = f"S3 upload of file '{escape(file)}' failed: {err}"
            LOG.exception(f"{escape(file)}: {err}")
        else:
            uploaded = True

        return uploaded, error

    @update_status
    def add_file_db(self, file):
        """Make API request to add file to DB."""
        # Variables
        added_to_db = False
        error = ""

        # Get file info and specify info required in db
        fileinfo = self.filehandler.data[file]
        LOG.debug(f"Fileinfo: {fileinfo}")
        params = {"project": self.project}
        file_info = {
            "name": file,
            "name_in_bucket": str(fileinfo["path_remote"]),
            "subpath": str(fileinfo["subpath"]),
            "size": fileinfo["size_raw"],
            "size_processed": fileinfo["size_processed"],
            "compressed": not fileinfo["compressed"],
            "salt": fileinfo["salt"],
            "public_key": fileinfo["public_key"],
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
            error = str(err)
            LOG.warning(error)
        else:
            # Error if failed
            if not response.ok:
                error = f"Failed to add file '{file}' to database: {response.text}"
                return added_to_db, error

            try:
                added_to_db, error = (True, response.json().get("message"))
            except simplejson.JSONDecodeError as err:
                error = str(err)
                LOG.warning(error)

        return added_to_db, error
