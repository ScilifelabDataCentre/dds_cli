"""Data getter."""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import logging
import pathlib

# Installed
import requests
import simplejson
from rich.markup import escape
from rich.progress import Progress, SpinnerColumn

# Own modules
from dds_cli import DDSEndpoint, FileSegment
from dds_cli import file_handler_remote as fhr
from dds_cli import data_remover as dr
from dds_cli import file_compressor as fc
from dds_cli import file_encryptor as fe
from dds_cli import text_handler as txt
from dds_cli.custom_decorators import verify_proceed, update_status, subpath_required
from dds_cli import base
import dds_cli.utils

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
        destination: pathlib.Path = pathlib.Path(""),
        silent: bool = False,
        verify_checksum: bool = False,
        method: str = "get",
        no_prompt: bool = False,
        token_path: str = None,
    ):
        """Handle actions regarding downloading data."""
        # Initiate DDSBaseClass to authenticate user
        super().__init__(
            project=project,
            dds_directory=destination,
            method=method,
            no_prompt=no_prompt,
            token_path=token_path,
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
                if self.temporary_folder and self.temporary_folder.is_dir():
                    LOG.debug(f"Deleting temporary folder {self.temporary_folder}.")
                    dds_utils.delete_folder(self.temporary_folder)
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

        LOG.debug(f"File {escape(str(file))} downloaded: {file_downloaded}")

        if file_downloaded:
            db_updated, message = self.update_db(file=file)
            LOG.debug(f"Database updated: {db_updated}")

            LOG.debug(f"Beginning decryption of file {escape(str(file))}...")
            file_saved = False
            with fe.Decryptor(
                project_keys=self.keys,
                peer_public=file_info["public_key"],
                key_salt=file_info["salt"],
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

            LOG.debug(f"file saved? {file_saved}")
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
        """Download files from the cloud."""
        downloaded = False
        error = ""
        file_local = self.filehandler.data[file]["path_downloaded"]
        file_remote = self.filehandler.data[file]["url"]

        try:
            with requests.get(file_remote, stream=True) as req:
                req.raise_for_status()
                with file_local.open(mode="wb") as new_file:
                    for chunk in req.iter_content(chunk_size=FileSegment.SEGMENT_SIZE_CIPHER):
                        progress.update(task, advance=len(chunk))
                        new_file.write(chunk)
        except (
            requests.exceptions.ConnectTimeout,
            requests.exceptions.HTTPError,
            requests.exceptions.ReadTimeout,
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError,
        ) as err:
            if (
                hasattr(err, "response")
                and hasattr(err.response, "status_code")
                and err.response.status_code == 404
            ):
                error = "File not found! Please report this to the SciLifeLab Data Centre."
            else:
                error = str(err)
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
        filename = {"name": fileinfo["name_in_db"]}
        params = {"project": self.project}

        # Send file info to API
        try:
            response = requests.put(
                DDSEndpoint.FILE_UPDATE,
                params=params,
                json=filename,
                headers=self.token,
                timeout=DDSEndpoint.TIMEOUT,
            )
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
