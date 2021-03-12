"""Remote file handler module"""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import logging
import sys
import os

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

        LOG.debug("collecting file info")
        try:
            response = requests.get(
                DDSEndpoint.FILE_INFO, headers=token, json=all_paths
            )
        except requests.ConnectionError as err:
            LOG.debug(err)
            os._exit(1)

        console = rich.console.Console()
        if not response.ok:
            console.print(response.text)
            os._exit(1)

        file_info = response.json()
        if "files" not in file_info:
            console.print("No files in response despite ok request.")

        for x in file_info["files"]:
            LOG.debug(x)

        return file_info["files"]
