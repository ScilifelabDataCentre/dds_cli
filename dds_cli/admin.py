"""Admin class, adds ."""

####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
###################################################################################################

# Standard library
import logging
import pathlib

# Installed
import requests
import simplejson


# Own modules
from dds_cli import DDSEndpoint
import dds_cli.exceptions
import dds_cli.base

####################################################################################################
# START LOGGING CONFIG ###################################################### START LOGGING CONFIG #
####################################################################################################

LOG = logging.getLogger(__name__)


####################################################################################################
# CLASSES ################################################################################ CLASSES #
####################################################################################################


class UserInviter(dds_cli.base.DDSBaseClass):
    """Admin class for adding users, etc."""

    def __init__(self, username: str = None, config: pathlib.Path = None, method: str = "invite"):

        # Initiate DDSBaseClass to authenticate user
        super().__init__(username=username, config=config, method=method)

        # Only method "create" can use the ProjectCreator class
        if self.method != "invite":
            raise dds_cli.exceptions.AuthenticationError(f"Unauthorized method: '{self.method}'")

    def add_user(self, email, role):
        """Invite user."""

        # Invite user
        try:
            response = requests.post(
                dds_cli.DDSEndpoint.USER_INVITE,
                headers=self.token,
                params={"email": email, "role": role},
            )

            response_json = response.json()

            LOG.info(response_json)
        except requests.exceptions.RequestException as reqerr:
            raise dds_cli.exceptions.ApiRequestError(str(reqerr))
        except simplejson.JSONDecodeError as jsonerr:
            raise dds_cli.exceptions.ApiResponseError(str(jsonerr))
