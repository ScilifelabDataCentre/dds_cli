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

# Installed

# Own modules
from cli_code import DDSEndpoint

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
    recipient: dataclasses.InitVar[str] = None
    token: dict = dataclasses.field(init=False)

    def __post_init__(self, password, project, recipient):
        # Authenticate user
        if None in [self.username, password, project]:
            sys.exit("Missing user information.")

        self.token = self.authenticate_user(password=password,
                                            facility=recipient is not None)

        # Approve project access
        self.verify_project_access(project=project)

    def authenticate_user(self, password, facility):
        """Authenticates the username and password via a call to the API."""

        response = requests.get(DDSEndpoint.AUTH,
                                params={"facility": facility},
                                auth=(self.username, password))

        if not response.ok:
            sys.exit("User authentication failed! "
                     f"Error code: {response.status_code} "
                     f" -- {response.reason}")

        token = response.json()
        return {"x-access-token": token["token"]}

    def verify_project_access(self, project):
        """docstring"""

        response = requests.get(DDSEndpoint.AUTH_PROJ,
                                params={"project": project},
                                headers=self.token)

        if not response.ok:
            sys.exit("Project access denied! "
                     f"Error code: {response.status_code} "
                     f" -- {response.reason} "
                     f" -- {response.request}\n\n"
                     f"{response.text}")

        dds_access = response.json()
        if not dds_access["dds-access-granted"]:
            sys.exit("Project access denied.")
