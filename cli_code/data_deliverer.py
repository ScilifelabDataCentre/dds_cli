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
import requests

# Installed
import botocore

# Own modules
from cli_code import user
from cli_code import file_handler as fh
from cli_code import s3_connector as s3
from cli_code import DDSEndpoint

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
        file_collector = fh.FileHandler(user_input=kwargs)

        self.user = dds_user
        self.data = file_collector
        self.project = project
        self.token = dds_user.token
        self.break_on_fail = kwargs["break_on_fail"] \
            if "break_on_fail" in kwargs else False

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

        self.set_upload_status(file=file)

        with s3.S3Connector(project_id=self.project, token=self.token) as conn:

            # Upload file
            try:
                conn.resource.meta.client.upload_file(
                    Filename=str(file),
                    Bucket=conn.bucketname,
                    Key=self.data.data[file]["name_in_bucket"],
                    ExtraArgs={
                        "ACL": "private",  # Access control list
                        "CacheControl": "no-store"  # Don't store cache
                    }
                )
            except botocore.client.ClientError as err:
                log.exception("Failed to upload file '%s': %s", file, err)
                self.cancel(file=file)  # TODO (ina): check out, confused atm
                return False

        log.info("Success: File '%s' uploaded!", file)
        return True

    def set_upload_status(self, file, started=True, done=False):
        """Updates the current files status"""

        if started and done:
            log.critical("Error! Upload marked as both 'started' and 'done' "
                         " for file '%s'", file)

        if not started and not done:
            log.critical("Error! Setting upload status to neither started or "
                         "done -- should not be possible. File: '%s'", file)

        if self.data.data[file]["status"]["do_fail"]["value"]:
            pass  # TODO (ina): Do something here

        new_status = {"started": started, "done": done}
        if self.data.data[file]["status"]["processing"]["done"]:
            self.data.data[file]["status"]["upload"].update(new_status)

    def cancel(self, file):
        """Cancels upload of single failed file or all"""

        if self.break_on_fail:
            # Cancel all
            pass
        else:
            # Cancel one
            pass


    def add_file_db(self, file):
        """Make API request to add file to DB."""

        # Get file info
        fileinfo = self.data.data[file]

        # Send file info to API
        response = requests.post(
            DDSEndpoint.NEWFILE,
            params={"name": fileinfo["name_in_db"],
                    "name_in_bucket": fileinfo["name_in_bucket"],
                    "subpath": fileinfo["subpath"],
                    "project": self.project},
            headers=self.token
        )

        # Error if failed
        if not response.ok:
            log.exception("Failed to add file '%s' to database! %s -- %s",
                          file, response.status_code, response.text)
            return False

        log.info("Success: File '%s' added to DB!", file)
        return True
