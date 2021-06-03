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

# Installed
import rich

# Own modules
from dds_cli import DDSEndpoint

###############################################################################
# START LOGGING CONFIG ################################# START LOGGING CONFIG #
###############################################################################

LOG = logging.getLogger(__name__)

###############################################################################
# RICH CONFIG ################################################### RICH CONFIG #
###############################################################################

console = rich.console.Console()

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
            console.print("\n:warning: Missing user information :warning:\n")
            os._exit(1)

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
            LOG.warning(err)
            raise SystemExit from err

        if not response.ok:
            console.print(f"\n:no_entry_sign: {response.text} :no_entry_sign:\n")
            os._exit(1)

        try:
            token = response.json()

            if "token" not in token:
                console.print("\n:warning: Missing token in authentication response :warning:\n")
                os._exit(1)
        except simplejson.JSONDecodeError as err:
            raise SystemExit from err

        LOG.debug(f"User {self.username} granted access to the DDS")

        return {"x-access-token": token["token"]}
