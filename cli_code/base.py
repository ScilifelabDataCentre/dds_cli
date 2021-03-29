"""Base class for the DDS CLI. Verifies the users access to the DDS."""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import inspect
import logging
import sys
import os

# Installed
import requests
import rich
import simplejson

# Own modules
from cli_code import file_handler as fh
from cli_code import user
from cli_code import DDSEndpoint
from cli_code import s3_connector as s3


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
# FUNCTIONS ####################################################### FUNCTIONS #
###############################################################################


def attempted_operation():
    """Gets the command entered by the user (e.g. put)."""

    curframe = inspect.currentframe()
    return inspect.getouterframes(curframe, 2)[3].function


###############################################################################
# CLASSES ########################################################### CLASSES #
###############################################################################


class DDSBaseClass:
    """Data Delivery System base class. For common operations."""

    def __init__(self, username=None, password=None, config=None, project=None):
        # Get attempted operation e.g. put/ls/rm/get
        self.method = attempted_operation()

        # Verify that user entered enough info
        username, password, self.project = self.__verify_input(
            username=username, password=password, config=config, project=project
        )

        # Authenticate the user and get the token
        dds_user = user.User(username=username, password=password, project=self.project)
        self.token = dds_user.token

        # Project access only required if trying to upload, download or list
        # files within project
        if (
            self.method == "put"
            or self.method == "get"
            or (self.method in ["ls", "rm"] and self.project is not None)
        ):
            self.token = self.__verify_project_access()

    # Private methods ############################### Private methods #
    def __verify_input(self, username=None, password=None, config=None, project=None):
        """Verifies that the users input is valid and fully specified."""

        LOG.debug("Verifying the user input...")

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
        if self.method in ["put", "get"] and project is None:
            console.print(
                "\n:warning: "
                "Data Delivery System project information is missing. "
                ":warning:\n"
            )
            os._exit(os.EX_OK)
        if username is None:
            console.print(
                "\n:warning: Data Delivery System options are missing :warning:\n"
            )
            os._exit(os.EX_OK)

        # Set password if missing
        if password is None:
            # password = getpass.getpass()
            password = "password"  # TODO: REMOVE - ONLY FOR DEV

        LOG.debug("...User input verified.")

        return username, password, project

    def __verify_project_access(self):
        """Verifies that the user has access to the specified project."""

        LOG.debug("Verifying access to project %s...", self.project)

        # Perform request to API
        try:
            response = requests.get(
                DDSEndpoint.AUTH_PROJ,
                params={"method": self.method},
                headers=self.token,
                timeout=DDSEndpoint.TIMEOUT,
            )
        except requests.exceptions.RequestException as err:
            LOG.warning(err)
            raise SystemExit from err

        # Problem
        if not response.ok:
            console.print(
                "\n:no_entry_sign: "
                f"Project access denied: {response.text} "
                ":no_entry_sign:\n"
            )
            os._exit(os.EX_OK)

        try:
            dds_access = response.json()
        except simplejson.JSONDecodeError as err:
            raise SystemExit from err

        # Access not granted
        if not dds_access["dds-access-granted"] or "token" not in dds_access:
            console.print("\n:no_entry_sign: Project access denied :no_entry_sign:\n")
            os._exit(os.EX_OK)

        LOG.debug("User has been granted access to project %s", self.project)

        return {"x-access-token": dds_access["token"]}

    # Public methods ################################# Public methods #
    def verify_bucket_exist(self):
        """Check that s3 connection works, and that bucket exists."""

        LOG.debug("Verifying and/or creating bucket.")

        with s3.S3Connector(project_id=self.project, token=self.token) as conn:

            if None in [conn.safespring_project, conn.keys, conn.bucketname, conn.url]:
                console.print(f"\n:warning: {conn.message} :warning:\n")
                os._exit(os.EX_OK)

            bucket_exists = conn.check_bucket_exists()
            if not bucket_exists:
                _ = conn.create_bucket()

        LOG.debug("Bucket created.")

        return True
