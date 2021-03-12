"""Remote file handler module"""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import logging
import sys
import os
import pathlib

# Installed
import requests
import rich

# Own modules
from cli_code import DDSEndpoint
from cli_code import file_handler as fh

###############################################################################
# START LOGGING CONFIG ################################# START LOGGING CONFIG #
###############################################################################

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)

###############################################################################
# CLASSES ########################################################### CLASSES #
###############################################################################


class RemoteFileHandler(fh.FileHandler):
    """Collects the files specified by the user."""

    # Magic methods ################ Magic methods #
    def __init__(self, user_input, token):

        # Initiate FileHandler from inheritance
        super().__init__(user_input=user_input)

        self.data_list = list(set(self.data_list))
        LOG.debug(self.data_list)

        if not self.data_list:
            sys.exit("No data specified.")

        self.data = self.__collect_file_info_remote(
            all_paths=self.data_list, token=token
        )
        self.data_list = None

    def __collect_file_info_remote(self, all_paths, token):
        """Get information on files in db."""

        # Get file info from db via API
        try:
            response = requests.get(
                DDSEndpoint.FILE_INFO, headers=token, json=all_paths
            )
        except requests.ConnectionError as err:
            LOG.fatal(err)
            os._exit(1)

        # Server error or error in response
        console = rich.console.Console()
        if not response.ok:
            console.print(response.text)
            os._exit(1)

        # Get file info from response
        file_info = response.json()
        if not all([x in file_info for x in ["files", "folders"]]):
            console.print("No files in response despite ok request.")

        # Cancel download of those files or folders not found in the db
        self.failed = {
            x: {"error": "Not found in DB."}
            for x in all_paths
            if x not in file_info["files"] and x not in file_info["folders"]
        }

        # Save info on files in dict and return
        data = {}
        for x in file_info["files"]:
            new_name = pathlib.Path(x[0]).name
            data[new_name] = {"name_in_bucket": x[1], "name_in_db": x[0]}

        for x, y in file_info["folders"].items():
            data.update({z[0]: {"name_in_bucket": z[1], "name_in_db": z[0]} for z in y})

        return data

    def create_download_status_dict(self):
        """Create dict for tracking file download status."""

        return "hej"