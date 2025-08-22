"""Data putter."""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import concurrent.futures
import itertools
import logging
import pathlib
import json

# Installed
import boto3
import botocore
from rich.markup import escape
from rich.progress import Progress, SpinnerColumn, BarColumn

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
import dds_cli.directory
import dds_cli.utils

###############################################################################
# START LOGGING CONFIG ################################# START LOGGING CONFIG #
###############################################################################

LOG = logging.getLogger(__name__)

###############################################################################
# MAIN FUNCTION ############################################### MAIN FUNCTION #
###############################################################################


def put(
    project,
    source,
    source_path_file,
    break_on_fail,
    overwrite,
    num_threads,
    silent,
    no_prompt,
    token_path,
    destination,
    staging_dir,
):
    """Handle upload of data."""
    # Initialize delivery - check user access etc
    with DataPutter(
        project=project,
        source=source,
        source_path_file=source_path_file,
        break_on_fail=break_on_fail,
        overwrite=overwrite,
        silent=silent,
        no_prompt=no_prompt,
        token_path=token_path,
        destination=destination,
        staging_dir=staging_dir,
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
                            LOG.debug("Future done for file: '%s'", escape(uploaded_file))

                            # Get result
                            try:
                                file_uploaded = fut.result()
                                LOG.debug(
                                    "Upload of '%s' successful: %s",
                                    escape(str(uploaded_file)),
                                    file_uploaded,
                                )
                            except concurrent.futures.BrokenExecutor as err:
                                LOG.error(
                                    "Upload of file '%s' failed! Error: %s",
                                    escape(uploaded_file),
                                    err,
                                )
                                continue

                            # Increase the main progress bar
                            progress.advance(upload_task)

                            # New available threads
                            new_tasks += 1

                        # Schedule the next set of futures for upload
                        for next_file in itertools.islice(iterator, new_tasks):
                            LOG.debug("Starting: '%s'", escape(next_file))
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

        # Make a single database update for files that have failed
        # Json file for failed files should only be created if there has been an error
        if putter.failed_delivery_log.is_file():
            LOG.warning(
                "Some file uploads experienced issues. The errors have been saved to the following file: %s.\n"
                "Investigating possible automatic solutions. Do not cancel the upload.",
                str(putter.failed_delivery_log),
            )
            try:
                putter.retry_add_file_db()
            except (
                dds_cli.exceptions.ApiRequestError,
                dds_cli.exceptions.ApiResponseError,
                dds_cli.exceptions.DDSCLIException,
            ) as err:
                LOG.warning(err)
            else:
                LOG.debug("Database retry finished.")


###############################################################################
# CLASSES ########################################################### CLASSES #
###############################################################################


class DataPutter(base.DDSBaseClass):
    """Data putter class."""

    def __init__(
        self,
        project: str = None,
        staging_dir: dds_cli.directory.DDSDirectory = None,
        break_on_fail: bool = False,
        overwrite: bool = False,
        source: tuple = (),
        source_path_file: pathlib.Path = None,
        silent: bool = False,
        method: str = "put",
        no_prompt: bool = False,
        token_path: str = None,
        destination: str = None,
    ):
        """Handle actions regarding upload of data."""
        # Initiate DDSBaseClass to authenticate user
        super().__init__(
            project=project,
            method=method,
            no_prompt=no_prompt,
            token_path=token_path,
            staging_dir=staging_dir,
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
                remote_destination=destination,
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
            if self.temporary_directory and self.temporary_directory.is_dir():
                LOG.debug("Deleting temporary folder %s.", self.temporary_directory)
                dds_cli.utils.delete_folder(self.temporary_directory)
            raise exceptions.UploadError(
                "The specified data has already been uploaded. If you wish to redo the upload, "
                "use the '--overwrite' flag. Please use with caution as previously uploaded data "
                "with matching file paths will be overwritten."
            )

    # Public methods ###################### Public methods #
    @verify_proceed
    @subpath_required
    def protect_and_upload(self, file, progress):
        """Process and upload the file while handling the progress bars."""
        # Variables
        all_ok, saved, message = (False, False, "")  # Error catching
        file_info = self.filehandler.data[file]  # Info on current file
        file_public_key, salt = ("", "")  # Crypto info
        file_path_raw = escape(str(file_info["path_raw"]))
        LOG.debug("Step '%s': started file '%s'", self.method, file_path_raw)

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
            LOG.debug("Encrypting file '%s'", file_path_raw)
            saved, message = encryptor.encrypt_filechunks(
                chunks=streamed_chunks,
                outfile=file_info["path_processed"],
                progress=(progress, task),
            )

            # Get hex version of public key -- saved in db
            file_public_key = encryptor.get_public_component_hex(private_key=encryptor.my_private)
            salt = encryptor.salt

        # Update file info incl size, public key, salt
        self.filehandler.data[file]["public_key"] = file_public_key
        self.filehandler.data[file]["salt"] = salt
        self.filehandler.data[file]["size_processed"] = file_info["path_processed"].stat().st_size

        LOG.debug(
            "File '%s' processed size: %s",
            file_path_raw,
            file_info["path_processed"].stat().st_size,
        )

        if saved:
            LOG.debug(
                "File successfully encrypted: '%s'",
                file_path_raw,
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
                        "File successfully uploaded and added to the database: '%s'",
                        file_path_raw,
                    )

        if not saved or all_ok:
            # Delete temporary processed file locally
            LOG.debug(
                "Deleting file '%s' - exists: %s",
                escape(str(file_info["path_processed"])),
                file_info["path_processed"].exists(),
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
        file_path_raw = self.filehandler.data[file]["path_raw"]
        LOG.debug("Step '%s': started file '%s'", self.method, file_path_raw)

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
                    Callback=(
                        status.ProgressPercentage(
                            progress=progress,
                            task=task,
                        )
                        if task is not None
                        else None
                    ),
                )
        except (
            botocore.client.ClientError,
            boto3.exceptions.Boto3Error,
            botocore.exceptions.BotoCoreError,
            FileNotFoundError,
            TypeError,
        ) as err:
            error = f"S3 upload of file '{escape(file)}' failed: {err}"
            LOG.exception("'%s': %s", escape(file), err)
        else:
            uploaded = True

        return uploaded, error

    @update_status
    def add_file_db(self, file):
        """Make API request to add file to DB."""
        # Variables
        added_to_db = False

        # Get file info and specify info required in db
        fileinfo = self.filehandler.data[file]
        params = {"project": self.project}
        file_info = {
            "name": pathlib.Path(file),
            "name_in_bucket": fileinfo["path_remote"],
            "subpath": fileinfo["subpath"],
            "size": fileinfo["size_raw"],
            "size_processed": fileinfo["size_processed"],
            "compressed": not fileinfo["compressed"],
            "salt": fileinfo["salt"],
            "public_key": fileinfo["public_key"],
            "checksum": fileinfo["checksum"],
        }

        # Send file info to API - post if new file, put if overwrite
        request_method = "put" if fileinfo["overwrite"] else "post"
        try:
            response_json, _ = dds_cli.utils.perform_request(
                DDSEndpoint.FILE_NEW,
                method=request_method,
                params=params,
                json=file_info,
                headers=self.token,
                error_message=f"Failed to add file '{file}' to database",
            )
            added_to_db, message = (True, response_json)
            LOG.debug("API call for file '%s: Adding to database'", fileinfo["path_raw"])
        except (
            dds_cli.exceptions.ApiRequestError,
            dds_cli.exceptions.ApiResponseError,
            dds_cli.exceptions.DDSCLIException,
        ) as err:
            message = str(err)
            LOG.warning(message)

        return added_to_db, message

    def retry_add_file_db(self):
        """Attempting to save the files to the database.

        This sends info to the API on all files that have been uploaded
        but where the 'add_file_db' failed for some reason.
        """
        LOG.info("Attempting to add the file to the database.")

        # Load json from file
        try:
            with self.failed_delivery_log.open(mode="r", encoding="utf-8") as json_f:
                failed = json.load(json_f)
        except Exception as err:
            raise dds_cli.exceptions.DDSCLIException(message=f"Failed to load file info: {err}")

        # Only keep 'add_file_db' as failed operation
        for file, values in failed.copy().items():
            if values.get("status", {}).get("failed_op") != "add_file_db":
                failed.pop(file)
        if len(failed) == 0:
            raise dds_cli.exceptions.DDSCLIException(
                message="No files failed due to 'add_file_db'."
            )

        # Send failed file info to API endpoint
        response, _ = dds_cli.utils.perform_request(
            DDSEndpoint.FILE_ADD_FAILED,
            method="put",
            headers=self.token,
            params={"project": self.project},
            json=failed,
            error_message="Failed to add missing files",
        )

        # Get info from response
        message = response.get("message")
        files_added = response.get("files_added")

        # Get successfully added files
        if len(files_added) == len(failed):
            LOG.info(
                "All successfully uploaded files were successfully added to the database during the retry."
            )
        elif len(message) == len(failed):
            LOG.warning("The retry did not add any of the failed files to the database.")
        else:
            LOG.warning("Some files failed to be updated in the database.")

        # Update status
        for file in files_added:
            self.status[file].update(
                {
                    "cancel": False,
                    "failed_op": None,
                    "message": "Added with 'retry_add_file_db'",
                }
            )
