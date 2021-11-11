"""User module."""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import dataclasses
import logging
import requests
import simplejson

# Own modules
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
    token: dict = dataclasses.field(init=False)

    def __post_init__(self, password):
        # Username and password required for user authentication
        if None in [self.username, password]:
            raise exceptions.MissingCredentialsException(
                missing="username" if not self.username else "password",
            )

        # Authenticate user and get delivery JWT token
        self.token = self.__authenticate_user(password=password)
        LOG.info(f"Token from {dds_cli.DDSEndpoint.TOKEN}: {self.token}")

    # Private methods ######################### Private methods #
    def __authenticate_user(self, password):
        """Authenticates the username and password via a call to the API."""

        LOG.debug(f"Authenticating the user: {self.username}")

        # Project passed in to add it to the token. Can be None.
        try:
            response = requests.get(
                dds_cli.DDSEndpoint.TOKEN,
                auth=(self.username, password),
                timeout=dds_cli.DDSEndpoint.TIMEOUT,
            )
            response_json = response.json()
        except requests.exceptions.RequestException as err:
            raise exceptions.ApiRequestError(message=str(err)) from err
        except simplejson.JSONDecodeError as err:
            raise dds_cli.exceptions.ApiResponseError(message=str(err))

        # Raise exceptions to log info if not ok response
        if not response.ok:
            message = response_json.get("message", "Unexpected error!")
            if response.status_code == 401:
                raise exceptions.AuthenticationError(message=message)

            raise exceptions.ApiResponseError(message=message)

        # Get token from response
        token = response_json.get("token")
        if not token:
            raise exceptions.TokenNotFoundError(message="Missing token in authentication response.")

        LOG.debug(f"User {self.username} granted access to the DDS")

        return {"Authorization": f"Bearer {token}"}
