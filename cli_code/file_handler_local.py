"""Local file handler module"""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import logging
import sys
import pathlib
import uuid
import os

# Installed
import requests
import rich
import simplejson

# Own modules
from cli_code import status
from cli_code import FileSegment
from cli_code import DDSEndpoint
from cli_code import file_handler as fh
from cli_code import file_compressor as fc
from cli_code.cli_decorators import subpath_required

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


class LocalFileHandler(fh.FileHandler):
    """Collects the files specified by the user."""

    # Magic methods ################ Magic methods #
    def __init__(self, user_input, temporary_destination):

        LOG.debug("Collecting file info...")

        # Initiate FileHandler from inheritance
        super().__init__(user_input=user_input, local_destination=temporary_destination)

        # Get absolute paths to all data and removes duplicates
        self.data_list = list(
            set(
                pathlib.Path(x).resolve()
                for x in self.data_list
                if pathlib.Path(x).exists()
            )
        )

        # No data -- cannot proceed
        if not self.data_list:
            console.print("\n:warning: No data specified. :warning:\n")
            os._exit(os.EX_OK)

        self.data, _ = self.__collect_file_info_local(all_paths=self.data_list)
        self.data_list = None

        LOG.debug("File info computed/collected")

    # Static methods ############## Static methods #
    @staticmethod
    def generate_bucket_filepath(filename="", folder=pathlib.Path("")):
        """Generates filename and new path which the file will be
        called in the bucket."""

        # Generate new file name
        new_name = "".join([str(uuid.uuid4().hex[:6]), "_", filename])

        return str(folder / pathlib.Path(new_name))

    # Private methods ############ Private methods #
    def __collect_file_info_local(
        self, all_paths, folder=pathlib.Path(""), task_name=""
    ):
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
                        os._exit(os.EX_OK)

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
                    }

            elif path.is_dir():
                content_info, _ = self.__collect_file_info_local(
                    all_paths=path.glob("*"),
                    folder=folder / pathlib.Path(path.name),
                )
                file_info.update({**content_info})

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

                filestream_funcname = (
                    "read_file" if self.data[x]["compressed"] else "compress_file"
                )
                status_dict[x] = {
                    "cancel": False,
                    "started": False,
                    "message": "",
                    filestream_funcname: {"started": False, "done": False},
                    "put": {"started": False, "done": False},
                    "add_file_db": {"started": False, "done": False},
                    "task": None,
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
                headers=token,
                json=files,
                timeout=DDSEndpoint.TIMEOUT,
            )
        except requests.exceptions.RequestException as err:
            LOG.warning(err)
            raise SystemExit from err

        if not response.ok:
            console.print(f"\n{response.text}\n")
            os._exit(os.EX_OK)

        try:
            files_in_db = response.json()
        except simplejson.JSONDecodeError as err:
            LOG.warning(err)
            raise SystemExit from err

        # API failure
        if "files" not in files_in_db:
            console.print("\n:warning: Files not returned from API. :warning:\n")
            os._exit(os.EX_OK)

        LOG.debug("Previous upload check finished.")

        return dict() if files_in_db["files"] is None else files_in_db["files"]

    def create_encrypted_name(
        self, raw_file: pathlib.Path, subpath: str = "", no_compression: bool = True
    ):
        """Create new file name to save encrypted file."""

        # New local file name
        old_suffix = raw_file.suffix
        new_suffix = f".{old_suffix if no_compression else 'zst'}"
        new_file_name = (
            self.local_destination
            / subpath
            / raw_file.with_suffix(new_suffix + ".ccp").name
        )

        return new_file_name

    @staticmethod
    def read_file(
        file: pathlib.Path, chunk_size: int = FileSegment.SEGMENT_SIZE_RAW
    ) -> (bytes):
        """Yields the file chunk by chunk."""

        with file.open(mode="rb") as infile:
            for chunk in iter(lambda: infile.read(chunk_size), b""):
                yield chunk
