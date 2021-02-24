"""User module."""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import getpass
import json
import logging
import pathlib
import sys
import requests
import dataclasses
import inspect

# Installed

# Own modules
from cli_code import DDSEndpoint

###############################################################################
# START LOGGING CONFIG ################################# START LOGGING CONFIG #
###############################################################################

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

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
        # Authenticate user
        if None in [self.username, password]:
            sys.exit("Missing user information.")

        self.token = self.__authenticate_user(password=password)

    # Private methods ######################### Private methods #
    def __authenticate_user(self, password):
        """Authenticates the username and password via a call to the API."""

        response = requests.get(DDSEndpoint.AUTH,
                                auth=(self.username, password))

        if not response.ok:
            sys.exit("User authentication failed! "
                     f"Error code: {response.status_code} "
                     f" -- {response.text}")

        token = response.json()
        return {"x-access-token": token["token"]}

    # Public methods ########################### Public methods #
    