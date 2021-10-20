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
import http


# Own modules
import dds_cli
import dds_cli.exceptions
import dds_cli.base

####################################################################################################
# START LOGGING CONFIG ###################################################### START LOGGING CONFIG #
####################################################################################################

LOG = logging.getLogger(__name__)


####################################################################################################
# CLASSES ################################################################################ CLASSES #
####################################################################################################


class AccountAdder(dds_cli.base.DDSBaseClass):
    """Admin class for adding users, etc."""

    def __init__(self, username: str = None, config: pathlib.Path = None, method: str = "add"):
        """Initialize, incl. user authentication."""
        # Initiate DDSBaseClass to authenticate user
        super().__init__(username=username, config=config, method=method)

        # Only method "add" can use the AccountAdder class
        if self.method != "add":
            raise dds_cli.exceptions.AuthenticationError(f"Unauthorized method: '{self.method}'")

    def add_user(self, email, role):
        """Invite user."""
        # Perform request to API
        try:
            response = requests.post(
                dds_cli.DDSEndpoint.USER_ADD,
                headers=self.token,
                json={"email": email, "role": role},
            )

            # Get response
            response_json = response.json()
            LOG.debug(response_json)
        except requests.exceptions.RequestException as err:
            raise dds_cli.exceptions.ApiRequestError(message=str(err))
        except simplejson.JSONDecodeError as err:
            raise dds_cli.exceptions.ApiResponseError(message=str(err))

        # Format response message
        if not response.ok:
            message = "Could not add user"
            if response.status_code == http.HTTPStatus.INTERNAL_SERVER_ERROR:
                raise dds_cli.exceptions.ApiResponseError(message=f"{message}: {response.reason}")

            raise dds_cli.exceptions.DDSCLIException(
                message=f"{message}: {response_json.get('message', 'Unexpected error!')}"
            )

        LOG.info(response_json.get("message", "User successfully added."))
