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


def outer_function(func):
    # TODO (ina): Checkout decorator for cancelling files?
    def inner_function(self, *args, **kwargs):
        print("RUNNING DECORATOR")
        to_return = func(self, *args, **kwargs)
        print("FINISHING DECORATOR")
        return to_return

    return inner_function


class DataDeliverer:
    """Data deliverer class."""

    def __init__(self, *args, **kwargs):

        # Quit if no delivery info is specified
        if not kwargs:
            sys.exit("Missing Data Delivery System user credentials.")

        # Get CLI arg
        self.method = sys._getframe().f_back.f_code.co_name
        if not self.method in ["put"]:
            sys.exit("Unauthorized method!")

        # Flags
        self.break_on_fail = kwargs["break_on_fail"] \
            if "break_on_fail" in kwargs else False

        # Get user info
        username, password, project, recipient, kwargs = \
            self.verify_input(user_input=kwargs)
        log.debug(kwargs)

        dds_user = user.User(username=username, password=password,
                             project=project, recipient=recipient)

        # Get file info
        file_collector = fh.FileHandler(user_input=kwargs)
        files_in_db = file_collector.get_existing_files(
            project=project, token=dds_user.token
        )

        self.user = dds_user
        self.data = file_collector
        self.status = self.create_status_dict(to_cancel=files_in_db)
        self.project = project
        self.token = dds_user.token

        # Control ok connection to S3
        self.prepare_s3()

        sys.exit()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if exc_type is not None:
            traceback.print_exception(exc_type, exc_value, tb)
            return False  # uncomment to pass exception through

        return True

    def __repr__(self):
        return f"<DataDeliverer proj:{self.project}>"
    
    @outer_function
    def prepare_s3(self):
        """Check that s3 connection works, and that bucket exists."""

        with s3.S3Connector(project_id=self.project, token=self.token) as conn:
            bucket_exists = conn.check_bucket_exists()
            if not bucket_exists:
                conn.create_bucket()

    def create_status_dict(self, to_cancel):
        """Create dict for tracking file delivery status"""

        if to_cancel and self.break_on_fail:
            sys.exit("Break-on-fail chosen. "
                     "File upload cancelled due to the following files: \n"
                     f"{to_cancel}")

        status_dict = {}
        for x, y in list(self.data.data.items()):
            cancel = bool(y["name_in_db"] in to_cancel)
            if cancel:
                self.data.failed[x] = {**self.data.data.pop(x),
                                       **{"message": "File already uploaded"}}
            else:
                status_dict[x] = {
                    "cancel": False,
                    "message": "",
                    "upload": {"started": False, "done": False},
                    "db": {"started": False, "done": False}
                }

        log.debug(status_dict)
        return status_dict

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

        # Do not upload if already cancelled
        cancel, message = self.set_file_status(file=file, task="upload")
        if cancel:
            self.cancel(file=file, message=message)
            return False, message

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
                message = f"S3 upload of file '{file}' failed!"
                log.exception("%s: %s", file, err)
                self.cancel(file=file, message=message)
                return False, message

        log.info("Success: File '%s' uploaded!", file)
        _, _ = self.set_file_status(file=file, task="upload",
                                    started=False, done=True)
        return True, ""

    def set_file_status(self, file, task, started=True, done=False):
        """Updates the current files status, and returns if to fail or not."""

        if task not in ["upload", "db"]:
            message = "Invalid status task: %s", task
            log.critical(message)
            return True, message

        if task == "db" and not self.status[file]["upload"]["done"]:
            message = "Trying to add file '%s' to db before file is uploaded.",\
                file
            log.critical(message)
            return True, message

        if started and done:
            message = "Error! Upload marked as both 'started' and 'done' " \
                " for file '%s'", file
            log.critical(message)
            return True

        if not started and not done:
            message = "Error! Setting upload status to neither started or " \
                "done -- should not be possible. File: '%s'", file
            log.critical(message)
            return True, message

        if self.status[file]["cancel"]:
            message = f"File cancelled. Error: {self.status[file]['message']}"
            log.info(message)
            return True, message

        # Update file status
        new_status = {"started": started, "done": done}
        self.status[file][task].update(new_status)
        log.info("Status change! '%s' : %s : %s", file, task, new_status)
        return False, ""

    def cancel(self, file, message):
        """Cancels upload of single failed file or all"""

        if self.break_on_fail:
            # Cancel all
            for curr_file, file_status in list(self.status.items()):
                # Cancel the current failed file
                if curr_file == file:
                    self.cancel_one(file=file, message=message)

                # Only cancel if upload has neither started or is finished
                # and the file isn't previously cancelled due to other problem
                if not any([file_status["upload"]["started"],
                            file_status["upload"]["done"]]):
                    if not file_status["cancel"]:
                        self.status[curr_file].update(
                            {"cancel": True,
                             "message": ("File upload cancelled due to the "
                                         f"file {file}. Break-on-fail chosen.")}
                        )
        else:
            # Cancel one
            self.cancel_one(file=file, message=message)

    def cancel_one(self, file, message):
        """Cancel one file"""

        if not self.status[file]["cancel"]:
            self.status[file].update({"cancel": True, "message": message})

    def add_file_db(self, file):
        """Make API request to add file to DB."""

        cancel, _ = self.set_file_status(file=file, task="db")
        log.debug("cancel? %s", cancel)
        if cancel:
            return False

        # Get file info
        fileinfo = self.data.data[file]

        # Send file info to API
        response = requests.post(
            DDSEndpoint.FILE_NEW,
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

        response_json = response.json()
        if "message" in response_json:
            log.info("Success: %s", response_json["message"])

        _ = self.set_file_status(file=file, task="db",
                                 started=False, done=True)
        return True
