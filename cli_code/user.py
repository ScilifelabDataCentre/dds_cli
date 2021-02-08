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


class User:
    """Authenticates the DDS user."""

    def __init__(self, username=None, password=None, project=None,
                 recipient=None):

        # Authenticate user
        if None in [username, password, project]:
            sys.exit("Missing user information.")

        token = self.authenticate_user(username=username, password=password,
                                       facility=recipient is not None)

        # Approve project access
        self.verify_project_access(project=project, token=token)

        # Set attributes
        self.username = username
        self.token = token

    def authenticate_user(self, username, password, facility):
        """Authenticates the username and password via a call to the API."""

        response = requests.get(DDSEndpoint.AUTH,
                                params={"facility": facility},
                                auth=(username, password))

        if not response.ok:
            sys.exit("User authentication failed! "
                     f"Error code: {response.status_code} "
                     f" -- {response.reason}")

        token = response.json()
        return {"x-access-token": token["token"]}

    def verify_project_access(self, project, token):
        """docstring"""

        response = requests.get(DDSEndpoint.AUTH_PROJ,
                                params={"project": project},
                                headers=token)

        if not response.ok:
            sys.exit("Project access denied! "
                     f"Error code: {response.status_code} "
                     f" -- {response.reason} "
                     f" -- {response.request}\n\n"
                     f"{response.text}")

        dds_access = response.json()
        if not dds_access["dds-access-granted"]:
            sys.exit("Project access denied.")
