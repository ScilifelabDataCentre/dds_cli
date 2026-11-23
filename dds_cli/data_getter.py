"""Data getter."""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import logging
import pathlib
import re
import time

# Installed
import requests
from rich.markup import escape
from rich.progress import Progress, SpinnerColumn

# Own modules
from dds_cli import constants
from dds_cli import DDSEndpoint, FileSegment
from dds_cli import file_handler_remote as fhr
from dds_cli import data_remover as dr
from dds_cli import file_compressor as fc
from dds_cli import file_encryptor as fe
from dds_cli import text_handler as txt
from dds_cli.custom_decorators import verify_proceed, update_status, subpath_required
from dds_cli import base
import dds_cli.utils
import dds_cli.exceptions

###############################################################################
# START LOGGING CONFIG ################################# START LOGGING CONFIG #
###############################################################################

LOG = logging.getLogger(__name__)

###############################################################################
# CLASSES ########################################################### CLASSES #
###############################################################################


class DataGetter(base.DDSBaseClass):
    """Data getter class."""

    def __init__(
        self,
        project: str = None,
        break_on_fail: bool = False,
        get_all: bool = False,
        source: tuple = (),
        source_path_file: pathlib.Path = None,
        silent: bool = False,
        verify_checksum: bool = False,
        method: str = "get",
        no_prompt: bool = False,
        token_path: str = None,
        staging_dir: dds_cli.directory.DDSDirectory = None,
    ):
        """Handle actions regarding downloading data."""
        # Initiate DDSBaseClass to authenticate user
        super().__init__(
            project=project,
            method=method,
            no_prompt=no_prompt,
            token_path=token_path,
            staging_dir=staging_dir,
        )

        # Initiate DataGetter specific attributes
        self.break_on_fail = break_on_fail
        self.verify_checksum = verify_checksum
        self.silent = silent
        self.filehandler = None

        # Only method "get" can use the DataGetter class
        if self.method != "get":
            raise dds_cli.exceptions.InvalidMethodError(
                attempted_method=self.method,
                message="DataGetter attempting unauthorized method",
            )

        # Start file prep progress
        with Progress(
            "[bold]{task.description}",
            SpinnerColumn(spinner_name="dots12", style="white"),
            console=dds_cli.utils.stderr_console,
        ) as progress:
            wait_task = progress.add_task("Collecting and preparing data", step="prepare")
            self.filehandler = fhr.RemoteFileHandler(
                get_all=get_all,
                user_input=(source, source_path_file),
                token=self.token,
                project=self.project,
                destination=self.dds_directory.directories["FILES"],
            )

            if self.filehandler.failed and self.break_on_fail:
                raise dds_cli.exceptions.DownloadError(
                    ":warning-emoji: Some specified files were not found in the system "
                    "and '--break-on-fail' flag used. :warning-emoji:"
                    f"Files not found: {self.filehandler.failed}"
                )

            if not self.filehandler.data:
                if self.temporary_directory and self.temporary_directory.is_dir():
                    LOG.debug("Deleting staging directory '%s'.", self.temporary_directory)
                    try:
                        dds_cli.utils.delete_folder(self.temporary_directory)
                    except OSError as err:
                        # Folder deletion may fail if log file is still being written to
                        # This is not critical - the important thing is to show the error message
                        LOG.error(
                            "Could not delete staging directory %s: %s",
                            self.temporary_directory,
                            err,
                        )
                raise dds_cli.exceptions.DownloadError("No files to download.")

            self.status = self.filehandler.create_download_status_dict()

            progress.remove_task(wait_task)

    # Public methods ############ Public methods #
    @verify_proceed
    @subpath_required
    def download_and_verify(self, file, progress):
        """Download the file, reveals the original data and verifies the integrity."""
        all_ok, message = (False, "")
        file_info = self.filehandler.data[file]
        file_name_in_db = escape(str(file_info["name_in_db"]))

        LOG.debug("Step 'download_and_verify': started file '%s'", file_name_in_db)
        # File task for downloading
        task = progress.add_task(
            description=txt.TextHandler.task_name(file=escape(str(file)), step="get"),
            total=file_info["size_stored"],
            visible=not self.silent,
        )

        # Perform download
        file_downloaded, message = self.get(file=file, progress=progress, task=task)

        # Update progress task for decryption
        progress.reset(
            task,
            description=txt.TextHandler.task_name(file=escape(str(file)), step="decrypt"),
            total=file_info["size_original"],
        )

        LOG.debug("File '%s' downloaded: %s", file_name_in_db, file_downloaded)

        # `get()` now verifies the on-disk byte count against `size_stored`
        # internally and only returns True if the file matches. If we reach
        # this branch, the encrypted-size check has already passed.
        # Defensive guard: make the contract explicit so a future refactor of
        # get() that breaks the size guarantee fails loudly here rather than
        # silently proceeding to decryption and surfacing as failed_op="crypto".
        if file_downloaded:
            actual_size = file_info["path_downloaded"].stat().st_size
            expected_size = file_info["size_stored"]
            if actual_size != expected_size:
                raise RuntimeError(
                    f"get() returned True but size mismatch for '{file_name_in_db}': "
                    f"expected {expected_size} bytes, got {actual_size} bytes"
                )
            db_updated, message = self.update_db(file=file)
            LOG.debug(
                "API call: database updated for file '%s': %s",
                file_name_in_db,
                db_updated,
            )

            LOG.debug("Beginning decryption of file '%s'...", file_name_in_db)
            file_saved = False
            with fe.Decryptor(
                project_keys=self.keys,
                peer_public=file_info["public_key"],
                key_salt=file_info["salt"],
                files_directory=self.dds_directory.directories["FILES"],
            ) as decryptor:
                streamed_chunks = decryptor.decrypt_file(
                    infile=file_info["path_downloaded"], outfile=file
                )

                stream_to_file_func = (
                    fc.Compressor.decompress_filechunks
                    if file_info["compressed"]
                    else self.filehandler.write_file
                )

                file_saved, message = stream_to_file_func(
                    chunks=streamed_chunks,
                    outfile=file,
                    files_directory=self.dds_directory.directories["FILES"],
                )

            LOG.debug("File '%s' saved? %s", file_name_in_db, file_saved)
            if file_saved:
                # Check file size post-decryption and post-decompression
                expected_size = file_info["size_original"]
                actual_size = pathlib.Path(file).stat().st_size
                if actual_size == expected_size:
                    LOG.debug(
                        "Decrypted file '%s' size matches expected size: %s bytes.",
                        file_name_in_db,
                        expected_size,
                    )
                else:
                    LOG.debug(
                        "Decrypted file '%s' size mismatch: expected %s bytes, got %s bytes",
                        file_name_in_db,
                        expected_size,
                        actual_size,
                    )
                # TODO (ina): decide on checksum verification method --
                # this checks original, the other is generated from compressed
                all_ok, message = (
                    fe.Encryptor.verify_checksum(
                        file=file,
                        correct_checksum=file_info["checksum"],
                        files_directory=self.dds_directory.directories["FILES"],
                    )
                    if self.verify_checksum
                    else (True, "")
                )

            dr.DataRemover.delete_tempfile(file=file_info["path_downloaded"])

        progress.remove_task(task)
        return all_ok, message

    @update_status
    def get(self, file, progress, task):
        """Download files from the cloud and verify the byte count.

        If an attempt is cut, the partial file is kept and the next attempt asks for the
        rest of the file with a Range request. The server must answer 206 with a matching
        Content-Range. If it answers 200, the whole file is downloaded again.
        A bad resume can not go unnoticed: decryption authenticates every chunk.

        Only attempts without progress count towards DOWNLOAD_MAX_RETRIES. Progress means
        that the partial file grew past the largest size reached so far, so a 200 that
        starts from zero again only counts as progress once it gets further than before.
        """
        downloaded = False
        error = ""
        file_info = self.filehandler.data[file]
        file_local = file_info["path_downloaded"]
        file_remote = file_info["url"]
        # The encrypted size on the bucket — what we expect on disk after the GET.
        # `size_original` is the plaintext size and is checked later, after decryption.
        expected_size = file_info["size_stored"]
        file_name_in_db = escape(str(file_info["name_in_db"]))

        # ChunkedEncodingError is included so that silent stream truncation
        # (raised manually below) hits the same backoff/retry path as a real
        # network error. Without it, a truncated body looked like a successful
        # download to requests/urllib3 and the retry loop never fired.
        retryable_exceptions = (
            requests.exceptions.ConnectTimeout,
            requests.exceptions.ReadTimeout,
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError,
            requests.exceptions.ChunkedEncodingError,
            dds_cli.exceptions.RangeResumeError,
        )

        max_failures = constants.DOWNLOAD_MAX_RETRIES
        backoff_factor = constants.DOWNLOAD_BACKOFF_FACTOR
        initial_wait = constants.DOWNLOAD_INITIAL_WAIT
        wait = initial_wait
        retry_messages = []
        cancelled = False
        attempt = 0
        failures = 0  # attempts in a row without progress
        largest_size = 0  # largest size of the partial file so far

        # Never resume from a file left by an earlier run: the object may have changed.
        self._remove_partial(file_local, file_name_in_db)

        while True:
            attempt += 1
            error = ""
            if self.service_unavailable:
                # Maintenance seen by another thread: don't start a new attempt.
                cancelled = True
                break
            offset = 0
            if attempt > 1:
                offset = self._resume_offset(file_local, expected_size, file_name_in_db)
                progress.reset(task, completed=offset)

            bytes_written = 0
            try:
                headers = {"Range": f"bytes={offset}-"} if offset else {}
                with requests.get(
                    file_remote,
                    stream=True,
                    headers=headers,
                    timeout=(constants.CONNECT_TIMEOUT, constants.READ_TIMEOUT),
                ) as req:
                    req.raise_for_status()
                    # Server-advertised body size. AWS S3 sets this on every GET,
                    # but S3-compatible backends behind a proxy may use chunked
                    # transfer encoding (no Content-Length) or send a malformed
                    # value. Treat both as "unknown" and rely on the size_stored
                    # check below to catch truncation in that case.
                    # For a 206 response this is the size of the rest of the file.
                    try:
                        content_length = int(req.headers.get("Content-Length", 0))
                    except (TypeError, ValueError):
                        content_length = 0

                    mode = "wb"
                    if offset:
                        if req.status_code == 206:
                            self._check_content_range(
                                content_range=req.headers.get("Content-Range"),
                                offset=offset,
                                expected_size=expected_size,
                                file_name_in_db=file_name_in_db,
                            )
                            mode = "ab"
                            LOG.info(
                                "Resuming download of '%s' at byte %s of %s.",
                                file_name_in_db,
                                offset,
                                expected_size,
                            )
                        else:
                            LOG.warning(
                                "Server did not resume the download of '%s' (HTTP %s). "
                                "Downloading the whole file again.",
                                file_name_in_db,
                                req.status_code,
                            )
                            offset = 0
                            progress.reset(task, completed=0)

                    with file_local.open(mode=mode) as new_file:
                        for chunk in req.iter_content(chunk_size=FileSegment.SEGMENT_SIZE_CIPHER):
                            if self.service_unavailable:
                                # Maintenance seen by another thread: stop this download.
                                cancelled = True
                                break
                            progress.update(task, advance=len(chunk))
                            new_file.write(chunk)
                            bytes_written += len(chunk)

                if cancelled:
                    break

                # Guard against silent truncation: requests/urllib3 do not
                # validate that bytes received == Content-Length. A clean TCP
                # FIN mid-stream otherwise looks like an EOF and the loop exits
                # successfully. Raise so the retry path catches us.
                if content_length and bytes_written != content_length:
                    raise requests.exceptions.ChunkedEncodingError(
                        f"Truncated download for '{file_name_in_db}': "
                        f"got {bytes_written} of {content_length} bytes"
                        + (f" (resumed at byte {offset})" if offset else "")
                    )

                # Cross-check against the size DDS recorded for the encrypted
                # blob. Doing it inside the retry loop means a mismatch retries
                # like any other transport error.
                actual_size = file_local.stat().st_size
                if actual_size != expected_size:
                    raise requests.exceptions.ChunkedEncodingError(
                        f"Size mismatch for '{file_name_in_db}': "
                        f"expected {expected_size} bytes, got {actual_size} bytes"
                    )
            except (requests.exceptions.HTTPError, *retryable_exceptions) as err:
                status_code = getattr(getattr(err, "response", None), "status_code", None)
                if isinstance(err, requests.exceptions.HTTPError) and status_code == 404:
                    error = "File not found! Please contact support."
                    break
                if isinstance(err, dds_cli.exceptions.RangeResumeError) or (
                    isinstance(err, requests.exceptions.HTTPError) and status_code == 416
                ):
                    # The partial file can not be trusted: start from byte zero next time.
                    self._remove_partial(file_local, file_name_in_db)
                error = str(err)
                size_now = self._partial_size(file_local)
                if size_now > largest_size:
                    # The attempt made progress, so this is a new cut and not a server
                    # that is down: start counting and the backoff again.
                    largest_size = size_now
                    failures = 0
                    wait = initial_wait
                    retry_messages = []
                else:
                    failures += 1
                    if failures >= max_failures:
                        break
                retry_msg = (
                    f"Download attempt {attempt} failed for '{file_name_in_db}' "
                    f"({failures}/{max_failures} without progress): {error}. "
                    f"Retrying in {wait}s..."
                )
                retry_messages.append(retry_msg)
                LOG.warning(retry_msg)
                time.sleep(wait)
                wait *= backoff_factor
            else:
                downloaded = True
                LOG.debug(
                    "Downloaded file '%s' size matches expected size: %s bytes.",
                    file_name_in_db,
                    expected_size,
                )
                break

        if cancelled:
            error = f"Service unavailable - download of '{file_name_in_db}' cancelled"
            LOG.warning(error)
            self._remove_partial(file_local, file_name_in_db)
        elif not downloaded and error:
            if retry_messages:
                error = " | ".join(retry_messages) + f" | Final error: {error}"
            LOG.error(
                "Download failed for '%s' after %d attempts: %s",
                file_name_in_db,
                attempt,
                error,
            )
            LOG.warning(
                "Download of '%s' could not be completed after %d attempts. "
                "Please ensure your internet connection is stable and that your "
                "computer does not enter sleep mode during large file transfers.",
                file_name_in_db,
                attempt,
            )
            # Don't leave a partial blob on disk after we've given up — it just
            # consumes space and risks being mistaken for a complete file.
            self._remove_partial(file_local, file_name_in_db)

        return downloaded, error

    @classmethod
    def _resume_offset(cls, file_local, expected_size, file_name_in_db):
        """Return the number of bytes we can keep from an earlier attempt (0 = start over)."""
        size = cls._partial_size(file_local)
        if 0 < size < expected_size:
            return size
        if size:
            # Same size or larger, but the attempt still failed: don't trust it.
            cls._remove_partial(file_local, file_name_in_db)
        return 0

    @staticmethod
    def _partial_size(file_local):
        """Return the size of the partial file, 0 if it does not exist."""
        try:
            return file_local.stat().st_size
        except OSError:
            return 0

    @staticmethod
    def _check_content_range(content_range, offset, expected_size, file_name_in_db):
        """Check that a 206 response starts at `offset` and covers the rest of the file.

        Expected format: 'bytes <start>-<end>/<total>' (RFC 9110).
        """
        match = re.fullmatch(r"\s*bytes\s+(\d+)-(\d+)/(\d+|\*)\s*", content_range or "")
        if not match:
            raise dds_cli.exceptions.RangeResumeError(
                f"Unexpected Content-Range for '{file_name_in_db}': {content_range!r}"
            )
        start, end, total = match.groups()
        if (
            int(start) != offset
            or int(end) != expected_size - 1
            or (total != "*" and int(total) != expected_size)
        ):
            raise dds_cli.exceptions.RangeResumeError(
                f"Content-Range mismatch for '{file_name_in_db}': got {content_range!r}, "
                f"expected 'bytes {offset}-{expected_size - 1}/{expected_size}'"
            )

    @staticmethod
    def _remove_partial(file_local, file_name_in_db):
        """Delete a partial download. Best-effort — never raises."""
        try:
            file_local.unlink(missing_ok=True)
        except OSError as unlink_err:
            # File-locking on Windows occasionally blocks unlink while the
            # progress bar still holds the path; we don't want this to mask
            # the real download error, so just log and move on.
            LOG.debug(
                "Could not remove partial download for '%s': %s",
                file_name_in_db,
                unlink_err,
            )

    @update_status
    def update_db(self, file):
        """Update file info in db."""
        updated_in_db = False

        # Get file info
        fileinfo = self.filehandler.data[file]
        filename = {"name": fileinfo["name_in_db"]}
        params = {"project": self.project}

        # Send file info to API.
        # Catch all API errors: a failed update must not stop the other downloads.
        # Exception: maintenance (ServiceUnavailableError) stops the files not started yet.
        try:
            response_json, _ = dds_cli.utils.perform_request_with_retry(
                DDSEndpoint.FILE_UPDATE,
                method="put",
                params=params,
                json=filename,
                headers=self.token,
                error_message="Failed to update file information",
            )
        except dds_cli.exceptions.ServiceUnavailableError as err:
            self.stop_for_maintenance(err)
            message = str(err)
        except (
            dds_cli.exceptions.ApiRequestError,
            dds_cli.exceptions.ApiResponseError,
            dds_cli.exceptions.DDSCLIException,
        ) as err:
            updated_in_db = False
            message = str(err)
        else:
            updated_in_db = True
            message = response_json["message"]

        return updated_in_db, message
