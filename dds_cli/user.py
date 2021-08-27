"""User module."""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import dataclasses
import logging
import os
import requests
import simplejson
import inspect

# Installed
import rich

# Own modules
from dds_cli import DDSEndpoint
import dds_cli
from dds_cli import exceptions

###############################################################################
# START LOGGING CONFIG ################################# START LOGGING CONFIG #
###############################################################################

LOG = logging.getLogger(__name__)

###############################################################################
# CLASSES ########################################################### CLASSES #
###############################################################################


@dataclasses.dataclass
class User:
    """Authenticates the DDS user."""

    username: str = None
    password: dataclasses.InitVar[str] = None
    project: dataclasses.InitVar[str] = None
    token: dict = dataclasses.field(init=False)

    def __post_init__(self, password, project):
        # Username and password required for user authentication
        if None in [self.username, password]:
            raise exceptions.MissingCredentialsException(
                missing="username" if not self.username else "password",
            )

        # Authenticate user and get delivery JWT token
        self.token = self.__authenticate_user(password=password, project=project)

    # Private methods ######################### Private methods #
    def __authenticate_user(self, password, project):
        """Authenticates the username and password via a call to the API."""

        LOG.debug(f"Authenticating the user: {self.username}")

        # Project passed in to add it to the token. Can be None.
        try:
            response = requests.get(
                DDSEndpoint.AUTH,
                params={"project": project},
                auth=(self.username, password),
                timeout=DDSEndpoint.TIMEOUT,
            )
        except requests.exceptions.RequestException as err:
            raise exceptions.ApiRequestError(message=str(err)) from err

        # Get response from api
        try:
            response_json = response.json()
        except simplejson.JSONDecodeError as err:
            LOG.exception(str(err))
            raise

        # Raise exceptions to log info if not ok response
        if not response.ok:
            message = response_json.get("message", "Unexpected error!")
            if response.status_code == 401:
                raise exceptions.AuthenticationError(message=message)
            else:
                raise exceptions.ApiResponseError(message=message)

        # Get token from response
        token = response_json.get("token")
        if not token:
            raise exceptions.TokenNotFoundError(message="Missing token in authentication response.")

        LOG.debug(f"User {self.username} granted access to the DDS")

        return {"x-access-token": token}
