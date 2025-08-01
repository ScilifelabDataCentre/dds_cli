"""Remote file handler module."""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import logging
import pathlib

# Installed

# Own modules
from dds_cli import DDSEndpoint
from dds_cli import file_handler as fh
import dds_cli.utils

###############################################################################
# START LOGGING CONFIG ################################# START LOGGING CONFIG #
###############################################################################

LOG = logging.getLogger(__name__)

###############################################################################
# CLASSES ########################################################### CLASSES #
###############################################################################


class RemoteFileHandler(fh.FileHandler):
    """Collects the files specified by the user."""

    # Magic methods ################ Magic methods #
    def __init__(self, get_all, user_input, token, project, destination=pathlib.Path("")):
        """Initialize FileHandler for collecting remote files."""
        # Initiate FileHandler from inheritance
        super().__init__(user_input=user_input, local_destination=destination, project=project)

        self.get_all = get_all

        self.data_list = list(set(self.data_list))

        if not self.data_list and not get_all:
            raise dds_cli.exceptions.NoDataError(
                "\n:warning-emoji: No data specified. :warning-emoji:\n"
            )

        self.data = self.__collect_file_info_remote(all_paths=self.data_list, token=token)
        self.data_list = None

    # Static methods ############ Static methods #
    @staticmethod
    def write_file(chunks, outfile: pathlib.Path, **_):
        """Write file chunks to file."""
        saved, message = (False, "")

        LOG.debug("Saving file...")
        try:
            with outfile.open(mode="wb+") as new_file:
                for chunk in chunks:
                    new_file.write(chunk)
        except OSError as err:
            message = str(err)
            LOG.exception(message)
        else:
            saved = True
            LOG.debug("File saved.")

        return saved, message

    # Private methods ############ Private methods #
    def __collect_file_info_remote(self, all_paths, token):
        """Get information on files in db."""
        # Get file info from db via API
        file_info, _ = dds_cli.utils.perform_request(
            DDSEndpoint.FILE_INFO_ALL if self.get_all else DDSEndpoint.FILE_INFO,
            method="get",
            params={"project": self.project},
            headers=token,
            json=all_paths,
            error_message="Failed to collect file information",
        )

        # Folder info required if specific files requested
        if all_paths and not all(x in file_info for x in ["files", "folder_contents", "not_found"]):
            raise dds_cli.exceptions.DDSCLIException(
                "Error in response. Not enough info returned despite ok request."
            )

        folder_contents = file_info.get("folder_contents", {})
        files = file_info.get("files")

        # Cancel download of those files or folders not found in the db
        self.failed = {
            x: {"error": "Not found in DB."}
            for x in all_paths
            if x not in files and x not in folder_contents
        }

        LOG.debug("API call: files not found in DB: %s", self.failed)

        # Save info on files in dict and return
        data = {
            self.local_destination
            / pathlib.Path(x): {
                **y,
                "name_in_db": x,
                "path_downloaded": self.local_destination
                / pathlib.Path(y["subpath"])
                / pathlib.Path(y["name_in_bucket"]),
            }
            for x, y in files.items()
        }

        # Save info on files in a specific folder and return
        for _, folder_item in folder_contents.items():
            data.update(
                {
                    self.local_destination
                    / pathlib.Path(j): {
                        **k,
                        "name_in_db": j,
                        "path_downloaded": self.local_destination
                        / pathlib.Path(k["subpath"])
                        / pathlib.Path(k["name_in_bucket"]),
                    }
                    for j, k in folder_item.items()
                }
            )

        return data

    # Public methods ############ Public methods #
    def create_download_status_dict(self):
        """Create dict for tracking file download status."""
        return {
            x: {
                "cancel": False,
                "started": False,
                "message": "",
                "failed_op": None,
                "get": {"started": False, "done": False},
                "update_db": {"started": False, "done": False},
            }
            for x in self.data
        }
