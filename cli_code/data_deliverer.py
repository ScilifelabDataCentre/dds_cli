"""Data deliverer."""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import getpass
import logging
import pathlib
import sys
import json

# Installed

# Own modules
from cli_code import user

###############################################################################
# START LOGGING CONFIG ################################# START LOGGING CONFIG #
###############################################################################

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)

###############################################################################
# CLASSES ########################################################### CLASSES #
###############################################################################


class DataDeliverer:
    """Data deliverer class."""

    def __init__(self, *args, **kwargs):

        # Quit if no delivery info is specified
        if not kwargs:
            sys.exit("Missing Data Delivery System user credentials.")

        self.method = sys._getframe().f_back.f_code.co_name
        LOG.debug("Method: %s", self.method)

        # Get user info
        username, password, project, recipient = \
            self.verify_input(user_input=kwargs)

        dds_user = user.User(username=username, password=password,
                             project=project, recipient=recipient)

    def verify_input(self, user_input):
        """Verifies that the users input is valid and fully specified."""

        username = None
        password = None
        project = None
        recipient = None

        # Get user info from kwargs
        if "username" in user_input and user_input["username"]:
            username = user_input["username"]
        if "project" in user_input and user_input["project"]:
            project = user_input["project"]
        if "recipient" in user_input and user_input["recipient"]:
            recipient = user_input["recipient"]

        # Get contents from file
        if "config" in user_input and user_input["config"]:
            configpath = pathlib.Path(user_input["config"]).resolve()
            if not configpath.exists():
                sys.exit("Config file does not exist.")

            # Get contents from file
            try:
                with configpath.open(mode="r") as cfp:
                    contents = json.load(cfp)
            except json.decoder.JSONDecodeError as err:
                sys.exit(f"Failed to get config file contents: {err}")

            # Get user credentials and project info if not already specified
            if username is None and "username" in contents:
                username = contents["username"]
            if project is None and "project" in contents:
                project = contents["project"]
            if recipient is None and "recipient" in contents:
                recipient = contents["recipient"]

            if "password" in contents:
                password = contents["password"]

        # Username and project info is minimum required info
        if None in [username, project]:
            sys.exit("Data Delivery System options are missing.")

        if password is None:
            password = getpass.getpass()

        # Recipient required for upload
        if self.method == "put" and recipient is None:
            sys.exit("Project owner/data recipient not specified.")

        return username, password, project, recipient
