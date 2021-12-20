"""Admin class, adds ."""

####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
###################################################################################################

# Standard library
import logging

# Installed
import http
import requests
import simplejson


# Own modules
import dds_cli
import dds_cli.auth
import dds_cli.base
import dds_cli.exceptions

####################################################################################################
# START LOGGING CONFIG ###################################################### START LOGGING CONFIG #
####################################################################################################

LOG = logging.getLogger(__name__)


####################################################################################################
# CLASSES ################################################################################ CLASSES #
####################################################################################################


class AccountManager(dds_cli.base.DDSBaseClass):
    """Admin class for adding users, etc."""

    def __init__(
        self, username: str, authenticate: bool = True, method: str = "add", no_prompt: bool = False
    ):
        """Initialize, incl. user authentication."""
        # Initiate DDSBaseClass to authenticate user
        super().__init__(
            username=username, authenticate=authenticate, method=method, no_prompt=no_prompt
        )

        # Only methods "add" and "delete" can use the AccountManager class
        if self.method not in ["add", "delete"]:
            raise dds_cli.exceptions.AuthenticationError(f"Unauthorized method: '{self.method}'")

    def add_user(self, email, role, project):
        """Invite new user or associate existing users with projects."""
        # Perform request to API
        json = {"email": email, "role": role}
        if project:
            json["project"] = project
        try:
            response = requests.post(
                dds_cli.DDSEndpoint.USER_ADD,
                headers=self.token,
                json=json,
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

    def delete_user(self, email):
        """Delete users from the system"""
        # Perform request to API
        json = {"email": email}

        try:
            response = requests.delete(
                dds_cli.DDSEndpoint.USER_DELETE,
                headers=self.token,
                json=json,
            )

            # Get response
            response_json = response.json()
            message = response_json["message"]

        except requests.exceptions.RequestException as err:
            raise dds_cli.exceptions.ApiRequestError(message=str(err))
        except simplejson.JSONDecodeError as err:
            raise dds_cli.exceptions.ApiResponseError(message=str(err))

        # Format response message
        if not response.ok:
            if response.status_code == http.HTTPStatus.INTERNAL_SERVER_ERROR:
                raise dds_cli.exceptions.ApiResponseError(message)
            else:
                raise dds_cli.exceptions.DDSCLIException(message)
        else:
            LOG.info(message)

    def delete_own_account(self):
        """Delete users from the system"""
        # Perform request to API

        try:
            response = requests.delete(
                dds_cli.DDSEndpoint.USER_DELETE_SELF,
                headers=self.token,
                json=None,
            )

            # Get response
            response_json = response.json()
            message = response_json["message"]

        except requests.exceptions.RequestException as err:
            raise dds_cli.exceptions.ApiRequestError(message=str(err))
        except simplejson.JSONDecodeError as err:
            raise dds_cli.exceptions.ApiResponseError(message=str(err))

        # Format response message
        if not response.ok:
            if response.status_code == http.HTTPStatus.INTERNAL_SERVER_ERROR:
                raise dds_cli.exceptions.ApiResponseError(message)
            else:
                raise dds_cli.exceptions.DDSCLIException(message)
        else:
            LOG.info(message)
