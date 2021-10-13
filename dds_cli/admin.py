"""Admin class, adds ."""

####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
###################################################################################################

# Standard library
import logging

# Installed
import requests

# Own modules
from dds_cli import DDSEndpoint
import dds_cli.exceptions

####################################################################################################
# START LOGGING CONFIG ###################################################### START LOGGING CONFIG #
####################################################################################################

LOG = logging.getLogger(__name__)


####################################################################################################
# CLASSES ################################################################################ CLASSES #
####################################################################################################


class Admin:
    """Admin class for adding users, etc."""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):

        # Don't clean up if we hit an exception
        if exc_type is not None:
            return False

        return True

    def add_user(self):
        LOG.info(self)

        try:
            response = requests.post(DDSEndpoint.USER_INVITE)
        except requests.exceptions.RequestException as reqerr:
            raise dds_cli.exceptions.ApiRequestError(message=str(reqerr))

        LOG.info(response.json())
