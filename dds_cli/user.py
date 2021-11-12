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
import stat

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

    username: str
    password: dataclasses.InitVar[str] = None
    token: dict = dataclasses.field(init=False)

    def __post_init__(self, password):

        # Fetch encrypted JWT token
        self.__retrieve_token(password)

    @property
    def token_dict(self):
        return {"Authorization": f"Bearer {self.token}"}

    # Private methods ######################### Private methods #
    def __retrieve_token(self, password):
        """Attempts to fetch saved token from file otherwise authenticate user and saves the new token."""

        LOG.debug(f"Retrieving token for user {self.username}")

        # Get token from file
        try:
            LOG.debug(f"Checking if token file exists for user {self.username}")
            self.token = self.__get_token_from_file()
        except dds_cli.exceptions.TokenNotFoundError as err:
            self.token = None

        # If token is not found, authenticate user and save token
        if not self.token:
            LOG.debug(f"No token found for user {self.username}, fetching new token from api")
            self.token = self.__authenticate_user(password)
            self.__save_token()

        return self.token

    def __authenticate_user(self, password):
        """Authenticates the username and password via a call to the API."""

        LOG.debug(f"Authenticating the user: {self.username}")
        # Username and password required for user authentication
        if None in [self.username, password]:
            raise exceptions.MissingCredentialsException(
                missing="username" if not self.username else "password",
            )

        # Project passed in to add it to the token. Can be None.
        try:
            response = requests.get(
                dds_cli.DDSEndpoint.ENCRYPTED_TOKEN,
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

        return token

    def __get_token_from_file(self):
        token_file = dds_cli.TOKEN_FILE

        if not token_file.is_file():
            return None

        # Verify permissions for token file
        permissions_ok, permissions = self.__check_token_file_permissions(token_file)
        if not permissions_ok:
            raise exceptions.DDSCLIException(
                message=f"Token file permissions are not properly set. Please remove {token_file} and rerun the command."
            )

        # Read token from file
        with token_file.open() as file:
            token = file.read()
            if not token:
                raise exceptions.TokenNotFoundError(message="Token file is empty.")

        LOG.debug(f"Token retrieved from file.")
        return token

    def __save_token(self):
        """Saves the token to the token file."""
        # Create token file if it does not exist
        token_file = dds_cli.TOKEN_FILE
        if not token_file.is_file():
            token_file.touch(mode=0o600)

        permissions_ok, permissions = self.__check_token_file_permissions(token_file)
        if not permissions_ok:
            raise exceptions.DDSCLIException(
                message=f"Token file permissions are not 600. Got {permissions}."
            )

        # Write the token to the file
        with token_file.open("w") as file:
            file.write(self.token)

    def __check_token_file_permissions(self, token_file):
        # Verify permissions for token file
        st_mode = os.stat(token_file).st_mode
        permissions = oct(stat.S_IMODE(st_mode))
        return permissions != 0o600, permissions
