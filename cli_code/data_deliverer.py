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
        # log.debug("File: %s, Status: %s", file, self.status)
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

        if not ok_to_continue:
            return False, message

        # Update status to done
        self.status[file][func.__name__].update({"done": True})

        return ok_to_continue, message

    return wrapped


def verify_bucket_exist(func):
    """Check that s3 connection works, and that bucket exists."""

    @functools.wraps(func)
    def wrapped(self, *args, **kwargs):

        with s3.S3Connector(project_id=self.project, token=self.token) as conn:
            bucket_exists = conn.check_bucket_exists()
            if not bucket_exists:
                _ = conn.create_bucket()

        return func(self, conn, *args, **kwargs)

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

    # Magic methods ########################## Magic methods #
    def __post_init__(self, *args):

        if not self.method in ["put"]:
            sys.exit("Unauthorized method!")

        # Get user info
        username, password, self.project, recipient, args = \
            self.verify_input(user_input=(self.project, ) + args)

        dds_user = user.User(username=username, password=password,
                             project=self.project, recipient=recipient)
        self.token = dds_user.token

        # Get file info
        self.data = fh.FileHandler(user_input=args)
        files_in_db = self.check_previous_upload()

        if files_in_db and self.break_on_fail:
            sys.exit("Some files have already been uploaded and "
                     f"'--break-on-fail' flag used. \n\nFiles: {files_in_db}")

        self.status = self.data.create_status_dict(existing_files=files_in_db)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if exc_type is not None:
            traceback.print_exception(exc_type, exc_value, tb)
            return False  # uncomment to pass exception through

        return True

    # General methods ###################### General methods #
    @verify_bucket_exist
    def check_previous_upload(self, *args, **kwargs):
        """Do API call and check for the files in the DB."""

        # Get files from db
        args = {"project": self.project}
        files = list(x for x in self.data.data)

        response = requests.get(DDSEndpoint.FILE_MATCH, params=args,
                                headers=self.token, json=files)

        if not response.ok:
            sys.exit("Failed to match previously uploaded files."
                     f"{response.status_code} -- {response.text}")

        files_in_db = response.json()

        # API failure
        if "files" not in files_in_db:
            sys.exit("Files not returned from API.")

        return list() if files_in_db["files"] is None else files_in_db["files"]

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
        file_local = str(self.data.data[file]["path_local"])
        file_remote = self.data.data[file]["name_in_bucket"]

        with s3.S3Connector(project_id=self.project, token=self.token) as conn:

            # Upload file
            try:
                conn.resource.meta.client.upload_file(
                    Filename=file_local,
                    Bucket=conn.bucketname,
                    Key=file_remote,
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
            params={"name": file,
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
