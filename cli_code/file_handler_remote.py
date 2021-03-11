"""Remote file handler module"""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import logging
import sys

# Installed


# Own modules
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
    def __init__(self, user_input):

        # Initiate FileHandler from inheritance
        super().__init__(user_input=user_input)

        self.data_list = list(set(self.data_list))
        LOG.debug(self.data_list)

        if not self.data_list:
            sys.exit("No data specified.")

        self.data = self.__collect_file_info_remote(all_paths=self.data_list)
        self.data_list = None

    def __collect_file_info_remote(self, all_paths):
        return all_paths
