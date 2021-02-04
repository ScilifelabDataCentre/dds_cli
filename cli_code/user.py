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

# Installed

# Own modules

###############################################################################
# START LOGGING CONFIG ################################# START LOGGING CONFIG #
###############################################################################

LOG = logging.getLogger(__name__)

###############################################################################
# CLASSES ########################################################### CLASSES #
###############################################################################


class User:
    """Authenticates the DDS user."""

    def __init__(self, config=None, username=None, project_id=None,
                 recipient=None):

        # Quit if no user credentials appears to be specified
        if config is None and username is None:
            sys.exit("Missing Data Delivery System user credentials.")

        # Define method - put
        self.method = sys._getframe().f_back.f_code.co_name
        LOG.debug("Method: %s", self.method)

        # Get user info
        self.username, self.password, self.project, self.recipient = \
            self.verify_input(config=config, username=username,
                              project=project_id, recipient=recipient)

    def verify_input(self, config, username, project, recipient):
        """Verifies that the users input is valid and fully specified."""

        password = None

        # Get info from config file if specified
        if config:
            configpath = pathlib.Path(config).resolve()
            if not configpath.exists():
                sys.exit("Config file does not exist.")

            # Get contents from file
            try:
                with configpath.open(mode="r") as cfp:
                    contents = json.load(cfp)
            except json.decoder.JSONDecodeError as err:
                sys.exit(f"Failed to get config file contents: {err}")

            # Get user credentials and project info
            if username is None and "username" in contents:
                username = contents["username"]
            if project is None and "project" in contents:
                project = contents["project"]
            if recipient is None and "recipient" in contents:
                recipient = contents["recipient"]

            if "password" in contents:
                password = contents["password"]

        if None in [username, project]:
            sys.exit("Data Delivery System options missing.")

        if password is None:
            password = getpass.getpass()

        if self.method == "put" and recipient is None:
            sys.exit("Project owner/data recipient not specified.")

        return username, password, project, recipient
