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
import functools
import dataclasses
import os
import inspect

# Installed
import botocore
import requests

# Own modules
from cli_code import user
from cli_code import base
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


class DataPutter(base.DDSBaseClass):
    """Data deliverer class."""

    def __init__(self, username: str = None, config: pathlib.Path = None,
                 project: str = None, break_on_fail: bool = False,
                 source: tuple = (), source_path_file: pathlib.Path = None):

        # Initiate DDSBaseClass to authenticate user
        super().__init__(username=username, config=config, project=project)
        
        # Initiate DataPutter specific attributes
        self.break_on_fail = break_on_fail
        self.data = None
        self.status = dict()

        # Only method "put" can use the DataPutter class
        if self.method != "put":
            sys.exit(f"Unauthorized method: {self.method}")

        # Get file info
        self.data = fh.FileHandler(user_input=(source, source_path_file))
        files_in_db = self.check_previous_upload()

        # Quit if error and flag
        if files_in_db and self.break_on_fail:
            sys.exit("Some files have already been uploaded and "
                     f"'--break-on-fail' flag used. \n\nFiles: {files_in_db}")

        # Generate status dict
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
        files = list(x for x in self.data.data)

        response = requests.get(DDSEndpoint.FILE_MATCH,
                                headers=self.token, json=files)

        if not response.ok:
            sys.exit("Failed to match previously uploaded files."
                     f"{response.status_code} -- {response.text}")

        files_in_db = response.json()

        # API failure
        if "files" not in files_in_db:
            sys.exit("Files not returned from API.")

        return list() if files_in_db["files"] is None else files_in_db["files"]

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
        # return False, message
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
                    "subpath": fileinfo["subpath"]},
            headers=self.token
        )

        # Error if failed
        if not response.ok:
            message = f"Failed to add file '{file}' to database! " \
                f"{response.status_code} -- {response.text}"
            log.exception(message)
            return False, message

        message = response.json()["message"]
        # return False, "test"
        return True, message
