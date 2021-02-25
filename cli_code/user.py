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
    project: dataclasses.InitVar[str] = None
    token: dict = dataclasses.field(init=False)

    def __post_init__(self, password, project):
        # Username and password required for user authentication
        if None in [self.username, password]:
            sys.exit("Missing user information.")

        # Authenticate user and get delivery JWT token
        self.token = self.__authenticate_user(password=password,
                                              project=project)

    # Private methods ######################### Private methods #
    def __authenticate_user(self, password, project):
        """Authenticates the username and password via a call to the API."""

        # Project passed in to add it to the token. Can be None.
        response = requests.get(DDSEndpoint.AUTH,
                                params={"project": project},
                                auth=(self.username, password))

        if not response.ok:
            sys.exit("User authentication failed! "
                     f"Error code: {response.status_code} "
                     f" -- {response.text}")

        token = response.json()
        return {"x-access-token": token["token"]}

    # Public methods ########################### Public methods #
