

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import inspect
import logging
import sys

# Installed
import requests

# Own modules
from cli_code import file_handler as fh
from cli_code import user
from cli_code import DDSEndpoint


###############################################################################
# START LOGGING CONFIG ################################# START LOGGING CONFIG #
###############################################################################

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


def attempted_operation():
    """Gets the command entered by the user (e.g. put)."""

    curframe = inspect.currentframe()
    return inspect.getouterframes(curframe, 2)[3].function


class DDSBaseClass:
    """Data Delivery System base class. For common operations."""

    def __init__(self, username=None, password=None, config=None, project=None):
        # Get attempted operation e.g. put/ls
        self.method = attempted_operation()

        # Verify that user entered enough info
        username, password, self.project = \
            self.__verify_input(username=username, password=password,
                                config=config, project=project)

        # Authenticate the user and get the token
        self.user = user.User(username=username, password=password,
                              project=self.project)
        self.token = self.user.token

        # Project access only required if trying to upload, download or list
        # files within project
        if self.method == "put" or \
                (self.method == "ls" and self.project is not None):
            self.token = self.__verify_project_access()

    # Private methods ############################### Private methods #
    def __verify_input(self, username=None, password=None, config=None,
                       project=None):
        """Verifies that the users input is valid and fully specified."""
        # Get contents from file
        if config is not None:
            # Get contents from file
            contents = fh.FileHandler.extract_config(configfile=config)

            # Get user credentials and project info if not already specified
            if username is None and "username" in contents:
                username = contents["username"]
            if project is None and "project" in contents:
                project = contents["project"]
            if password is None and "password" in contents:
                password = contents["password"]

        # Username and project info is minimum required info
        if self.method == "put" and project is None:
            sys.exit("Data Delivery System project information is missing.")
        if username is None:
            sys.exit("Data Delivery System options are missing.")

        # Set password if missing
        if password is None:
            # password = getpass.getpass()
            password = "password"   # TODO: REMOVE - ONLY FOR DEV

        return username, password, project

    def __verify_project_access(self):
        """Verifies that the user has access to the specified project."""

        response = requests.get(DDSEndpoint.AUTH_PROJ,
                                params={"method": self.method},
                                headers=self.token)

        if not response.ok:
            sys.exit("Project access denied! "
                     f"Error code: {response.status_code} "
                     f" -- {response.text}")

        dds_access = response.json()
        if not dds_access["dds-access-granted"] or "token" not in dds_access:
            sys.exit("Project access denied.")
        
        return {"x-access-token": dds_access["token"]}
        


    # Public methods ################################# Public methods #
