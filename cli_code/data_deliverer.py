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
import traceback

# Installed
import botocore

# Own modules
from cli_code import user
from cli_code import file_handler as fh
from cli_code import s3_connector as s3

###############################################################################
# START LOGGING CONFIG ################################# START LOGGING CONFIG #
###############################################################################

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

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
        if not self.method in ["put"]:
            sys.exit("Unauthorized method!")

        # Get user info
        username, password, project, recipient, kwargs = \
            self.verify_input(user_input=kwargs)
        log.debug(kwargs)

        dds_user = user.User(username=username, password=password,
                             project=project, recipient=recipient)

        # Get file info
        file_collector = fh.FileCollector(user_input=kwargs)

        self.user = dds_user
        self.data = file_collector
        self.project = project
        self.token = dds_user.token

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if exc_type is not None:
            traceback.print_exception(exc_type, exc_value, tb)
            return False  # uncomment to pass exception through

        return True

    def __repr__(self):
        return f"<DataDeliverer proj:{self.project}>"

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

            if password is None and "password" in contents:
                password = contents["password"]

        # Username and project info is minimum required info
        if None in [username, project]:
            sys.exit("Data Delivery System options are missing.")

        if password is None:
            # password = getpass.getpass()
            password = "password"   # TODO: REMOVE - ONLY FOR DEV

        # Recipient required for upload
        if self.method == "put" and recipient is None:
            sys.exit("Project owner/data recipient not specified.")

        # Only keep the data input in the kwargs
        [user_input.pop(x, None) for x in
         ["username", "password", "project", "recipient", "config"]]

        return username, password, project, recipient, user_input

    def put(self, file):
        """Uploads files to the cloud."""
        
        with s3.S3Connector(project_id=self.project, token=self.token) as conn:
            
            # Upload file
            try:
                conn.resource.meta.client.upload_file(
                    Filename=str(file),
                    Bucket=conn.bucketname,
                    Key="testfile_128.txt"
                )
            except botocore.client.ClientError as err:
                sys.exit(f"Failed to upload file '{file}'! {err}")

        return True
