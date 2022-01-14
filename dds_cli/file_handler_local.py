"""Local file handler module"""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import hashlib
import logging
import os
import pathlib
import uuid
import http

# Installed
import requests
import simplejson

# Own modules
from dds_cli import DDSEndpoint
from dds_cli import file_compressor as fc
from dds_cli import file_handler as fh
from dds_cli import FileSegment
from dds_cli import exceptions
import dds_cli.utils
from dds_cli import cli_decorators

###############################################################################
# START LOGGING CONFIG ################################# START LOGGING CONFIG #
###############################################################################

LOG = logging.getLogger(__name__)

###############################################################################
# CLASSES ########################################################### CLASSES #
###############################################################################


class LocalFileHandler(fh.FileHandler):
    """Collects the files specified by the user."""

    # Magic methods ################ Magic methods #
    def __init__(self, user_input, temporary_destination, project):

        LOG.debug("Collecting file info...")

        # Initiate FileHandler from inheritance
        super().__init__(
            user_input=user_input, local_destination=temporary_destination, project=project
        )

        # Remove duplicates and save all files for later use
        all_files = set(self.data_list)

        # Remove non existent files
        self.data_list = {x for x in self.data_list if pathlib.Path(x).exists()}

        non_existent_files = all_files.difference(self.data_list)
        if len(non_existent_files) > 0:
            # Issue warning that some of the files don't exist
            LOG.warning(
                "The following files from '{}' does not exist: '{}'".format(
                    user_input[1], "', '".join(non_existent_files)
                )
            )

        # Get absolute paths for all data
        self.data_list = [
            pathlib.Path(os.path.abspath(os.path.expanduser(path))) for path in self.data_list
        ]

        # No data -- cannot proceed
        if not self.data_list:
            dds_cli.utils.console.print("\n:warning-emoji: No data specified. :warning-emoji:\n")
            os._exit(1)

        self.data, _ = self.__collect_file_info_local(all_paths=self.data_list)
        self.data_list = None

        LOG.debug("File info computed/collected")

    # Static methods ############## Static methods #
    @staticmethod
    def generate_bucket_filepath(filename="", folder=pathlib.Path("")):
        """Generates filename and new path which the file will be
        called in the bucket."""

        # Generate new file name
        new_name = str(folder / pathlib.Path(str(uuid.uuid5(uuid.NAMESPACE_X500, filename))))

        # maximum allowed length of S3 object key is 1024 bytes in UTF-8
        if len(new_name.encode("utf-8")) > 1024:
            # because UTF-8 is a variable length encoding, some characters may take up 4 bytes.
            # Also mind that umlauts like ö or å will be encoded to 2 bytes each in Windows/Linux but to 3 bytes each on Mac,
            # because Windows/Linux use Normal-Form-Composed (NFC) Unicode, MacOS uses Normal-Form-Decomposed (NFD) Unicode.
            raise exceptions.S3KeyLengthExceeded(str(folder / pathlib.Path(filename)))
        else:
            return new_name

    @staticmethod
    def read_file(file, chunk_size: int = FileSegment.SEGMENT_SIZE_RAW):
        """Read file in chunk_size sized chunks.

        Raises:
        - OSError
        """

        try:
            with file.open(mode="rb") as infile:
                for chunk in iter(lambda: infile.read(chunk_size), b""):
                    yield chunk
        except OSError as err:
            LOG.warning(str(err))

    # Private methods ############ Private methods #
    def __collect_file_info_local(self, all_paths, folder=pathlib.Path(""), task_name=""):
        """Get info on each file in each path specified."""

        file_info = dict()
        progress_tasks = dict()
        for path in all_paths:
            task_name = path.name if folder == pathlib.Path("") else task_name
            # Get info for all files
            # and feed back to same function for all folders
            if path.is_file():
                with fc.Compressor() as compressor:
                    is_compressed, error = compressor.is_compressed(file=path)

                    if error != "":
                        LOG.exception(error)
                        os._exit(1)

                path_processed = self.create_encrypted_name(
                    raw_file=path,
                    subpath=folder,
                    no_compression=is_compressed,
                )

                file_info[str(folder / path.name)] = {
                    "path_raw": path,
                    "subpath": folder,
                    "size_raw": path.stat().st_size,
                    "compressed": is_compressed,
                    "path_processed": path_processed,
                    "size_processed": 0,
                    "path_remote": self.generate_bucket_filepath(
                        filename=path_processed.name, folder=folder
                    ),
                    "overwrite": False,
                    "checksum": "",
                }

            elif path.is_dir():
                content_info, _ = self.__collect_file_info_local(
                    all_paths=path.glob("*"),
                    folder=folder / pathlib.Path(path.name),
                )
                file_info.update({**content_info})
            else:
                if path.is_symlink():
                    try:
                        resolved = path.resolve()
                    except RuntimeError:
                        LOG.warning(
                            f"IGNORED: Link: {path} seems to contain infinite loop, will be ignored."
                        )
                    else:
                        LOG.warning(
                            f"IGNORED: Link: {path} -> {resolved} seems to be broken, will be ignored."
                        )
                else:
                    LOG.warning(
                        f"IGNORED: Path of unsupported/unknown type: {path}, will be ignored."
                    )

        return file_info, progress_tasks

    # Public methods ############## Public methods #
    def create_upload_status_dict(self, existing_files, overwrite=False):
        """Create dict for tracking file delivery status"""

        LOG.debug("Creating the status dictionary.")

        status_dict = {}
        for x in list(self.data):
            in_db = bool(x in existing_files)
            if in_db and not overwrite:
                self.failed[x] = {
                    **self.data.pop(x),
                    **{"message": "File already uploaded"},
                }
            else:
                if in_db:
                    if overwrite:
                        self.data[x].update(
                            {
                                "overwrite": True,
                                "path_remote": existing_files[x],
                            }
                        )

                # filestream_funcname = (
                #     "read_file" if self.data[x]["compressed"] else "compress_file"
                # )
                status_dict[x] = {
                    "cancel": False,
                    "started": False,
                    "message": "",
                    "failed_op": None,
                    # filestream_funcname: {"started": False, "done": False},
                    "put": {"started": False, "done": False},
                    "add_file_db": {"started": False, "done": False},
                    # "task": None,
                }

        LOG.debug("Initial statuses created.")

        return status_dict

    def check_previous_upload(self, token):
        """Do API call and check for the files in the DB."""

        LOG.debug("Checking if files have been previously uploaded.")

        # Get files from db
        files = list(x for x in self.data)
        try:
            response = requests.get(
                DDSEndpoint.FILE_MATCH,
                params={"project": self.project},
                headers=token,
                json=files,
                timeout=DDSEndpoint.TIMEOUT,
            )
        except requests.exceptions.RequestException as err:
            LOG.warning(err)
            raise SystemExit from err

        if not response.ok:
            message = "Failed getting information about previously uploaded files"
            if response.status_code == http.HTTPStatus.INTERNAL_SERVER_ERROR:
                raise exceptions.ApiResponseError(message=f"{message}: {response.reason}")

            raise exceptions.DDSCLIException(message=f"{message}: {response.json().get('message')}")

        try:
            files_in_db = response.json()
        except simplejson.JSONDecodeError as err:
            LOG.warning(err)
            raise SystemExit from err

        # API failure
        if "files" not in files_in_db:
            dds_cli.utils.console.print(
                "\n:warning-emoji: Files not returned from API. :warning-emoji:\n"
            )
            os._exit(1)

        LOG.debug("Previous upload check finished.")

        return dict() if files_in_db["files"] is None else files_in_db["files"]

    def create_encrypted_name(
        self, raw_file: pathlib.Path, subpath: str = "", no_compression: bool = True
    ):
        """Create new file name to save encrypted file."""

        # New local file name
        old_suffix = "".join(raw_file.suffixes)
        new_suffix = old_suffix if no_compression else f"{old_suffix}.zst"
        new_file_name = (
            self.local_destination / subpath / raw_file.with_suffix(new_suffix + ".ccp").name
        )

        return new_file_name

    def stream_raw_data(self, file):
        """Stream raw data from file."""
        # Get info for current file
        file_info = self.data[file]

        # Stream chunks while generating checksum from raw data
        checksum = hashlib.sha256()
        for chunk in self.read_file(file=file_info["path_raw"]):
            checksum.update(chunk)
            yield chunk

        # Update checksum in file info
        self.data[file]["checksum"] = checksum.hexdigest()

    def stream_compressed_data(self, file):
        """Stream compressed data from file."""
        # Get info for current file
        file_info = self.data[file]

        # Generate checksum
        checksum = hashlib.sha256()
        for chunk in self.read_file(file=file_info["path_raw"]):
            checksum.update(chunk)

        # Stream compressed chunks
        for chunk in fc.Compressor.compress_file(file=file_info["path_raw"]):
            yield chunk

        # Update checksum in file info
        self.data[file]["checksum"] = checksum.hexdigest()

    def save_streamed_chunks(self, chunks, outfile):
        """Save chunks to file."""
        with outfile.open(mode="wb+") as out:
            for chunk in chunks:
                out.write(chunk)
