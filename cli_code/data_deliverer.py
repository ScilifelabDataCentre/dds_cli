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
import functools
import time
import dataclasses
import os

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
# DECORATORS ##################################################### DECORATORS #
###############################################################################


def verify_proceed(func):
    """Decorator for verifying that the file is not cancelled.
    Also cancels the upload of all non-started files if break-on-fail."""

    @functools.wraps(func)
    def wrapped(self, *args, **kwargs):

        # Check that function has correct args
        if "file" not in kwargs:
            raise Exception("Missing key word argument in wrapper over "
                            f"function {func.__name__}: 'file'")
        file = kwargs["file"]

        # Return if file cancelled by another file
        if self.status[file]["cancel"]:
            message = f"File already cancelled, stopping upload " \
                f"of file {file}"
            log.warning(message)
            return False

        # Run function
        ok_to_proceed, message = func(self, *args, **kwargs)

        # Cancel file(s) if something failed
        if not ok_to_proceed:
            self.status[file].update({"cancel": True, "message": message})
            if self.break_on_fail:
                message = f"Cancelling upload due to file '{file}'. " \
                    "Break-on-fail specified in call."
                _ = [self.status[x].update({"cancel": True, "message": message})
                     for x in self.status if not self.status[x]["cancel"]
                     and not any([self.status[x]["put"]["started"],
                                  self.status[x]["put"]["done"]])
                     and x != file]

            log.debug("Status updated: %s", self.status[file])

        return ok_to_proceed

    return wrapped


def update_status(func):
    """Decorator for updating the status of files."""

    @functools.wraps(func)
    def wrapped(self, *args, **kwargs):

        # Check that function has correct args
        if "file" not in kwargs:
            raise Exception("Missing key word argument in wrapper over "
                            f"function {func.__name__}: 'file'")
        file = kwargs["file"]

        if func.__name__ not in ["put", "add_file_db"]:
            raise Exception(f"The function {func.__name__} cannot be used with"
                            " this decorator.")
        if func.__name__ not in self.status[file]:
            raise Exception(f"No status found for function {func.__name__}.")

        # Update status to started
        self.status[file][func.__name__].update({"started": True})

        # Run function
        ok_to_continue, message, *info = func(self, *args, **kwargs)

        log.debug("ok to contiue %s: %s", func.__name__, ok_to_continue)
        log.debug("message: %s", message)
        log.debug("Returned: %s", info)

        if not ok_to_continue:
            return False, message

        # Update status to done
        self.status[file][func.__name__].update({"done": True})

        return ok_to_continue, message

    return wrapped


###############################################################################
# CLASSES ########################################################### CLASSES #
###############################################################################


@dataclasses.dataclass
class DataDeliverer:
    """Data deliverer class."""

    method: str = "put"
    break_on_fail: bool = False
    project: str = None
    data: dict = dataclasses.field(init=False)
    status: dict = dataclasses.field(init=False)
    token: dict = dataclasses.field(init=False)
    username: dataclasses.InitVar[str] = None
    password: dataclasses.InitVar[str] = None
    recipient: dataclasses.InitVar[str] = None
    config: dataclasses.InitVar[pathlib.Path] = None
    source: dataclasses.InitVar[tuple] = None
    source_path_file: dataclasses.InitVar[pathlib.Path] = None

    def __post_init__(self, *args, **kwargs):

        if not self.method in ["put"]:
            sys.exit("Unauthorized method!")

        # Get user info
        username, password, self.project, recipient, args = \
            self.verify_input(user_input=(self.project, ) + args)

        dds_user = user.User(username=username, password=password,
                             project=self.project, recipient=recipient)
        
        # Get file info
        file_collector = fh.FileHandler(user_input=args)
        files_in_db = file_collector.get_existing_files(
            project=self.project, token=dds_user.token
        )

        # self.user = dds_user
        self.data = file_collector
        self.status = self.create_status_dict(to_cancel=files_in_db)
        self.token = dds_user.token

        self.prepare_s3()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if exc_type is not None:
            traceback.print_exception(exc_type, exc_value, tb)
            return False  # uncomment to pass exception through

        return True

    def prepare_s3(self):
        """Check that s3 connection works, and that bucket exists."""

        with s3.S3Connector(project_id=self.project, token=self.token) as conn:
            bucket_exists = conn.check_bucket_exists()
            if not bucket_exists:
                _ = conn.create_bucket()

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
                    "put": {"started": False, "done": False},
                    "add_file_db": {"started": False, "done": False}
                }

        log.debug(status_dict)
        return status_dict

    def verify_input(self, user_input):
        """Verifies that the users input is valid and fully specified."""

        project, username, password, recipient, config, *args = user_input

        # Get contents from file
        if config is not None:
            configpath = pathlib.Path(config).resolve()
            if not configpath.exists():
                sys.exit("Config file does not exist.")

            # Get contents from file
            try:
                original_umask = os.umask(0)
                with configpath.open(mode="r") as cfp:
                    contents = json.load(cfp)
            except json.decoder.JSONDecodeError as err:
                sys.exit(f"Failed to get config file contents: {err}")
            finally:
                os.umask(original_umask)

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

        return username, password, project, recipient, args

    @verify_proceed
    @update_status
    def put(self, file):
        """Uploads files to the cloud."""

        message = ""

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
                return False, message

        return True, message

    @verify_proceed
    @update_status
    def add_file_db(self, file):
        """Make API request to add file to DB."""

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
            message = f"Failed to add file '{file}' to database! " \
                f"{response.status_code} -- {response.text}"
            log.exception(message)
            return False, message

        message = response.json()["message"]
        return True, message
