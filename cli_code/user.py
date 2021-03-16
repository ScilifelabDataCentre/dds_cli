"""User module."""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import logging
import sys
import dataclasses
import os
import requests

# Installed
import rich

# Own modules
from cli_code import DDSEndpoint

###############################################################################
# START LOGGING CONFIG ################################# START LOGGING CONFIG #
###############################################################################

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)

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
            os._exit(os.EX_OK)

        # Authenticate user and get delivery JWT token
        self.token = self.__authenticate_user(password=password, project=project)

    # Private methods ######################### Private methods #
    def __authenticate_user(self, password, project):
        """Authenticates the username and password via a call to the API."""

        # Project passed in to add it to the token. Can be None.
        response = requests.get(
            DDSEndpoint.AUTH,
            params={"project": project},
            auth=(self.username, password),
        )

        if not response.ok:
            console.print(f"\n:no_entry_sign: {response.text} :no_entry_sign:\n")
            os._exit(os.EX_OK)

        token = response.json()

        if "token" not in token:
            console.print(
                "\n:warning: Missing token in authentication response :warning:\n"
            )
            os._exit(os.EX_OK)

        return {"x-access-token": token["token"]}

    # Public methods ########################### Public methods #
