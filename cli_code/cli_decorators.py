"""Module for all decorators related to the execution of the DDS CLI."""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import logging
import functools
import sys
import os
import pathlib

# Installed
import boto3
import botocore

# Own modules
from cli_code import s3_connector as s3
from cli_code import text_handler as txt

###############################################################################
# START LOGGING CONFIG ################################# START LOGGING CONFIG #
###############################################################################

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)

###############################################################################
# DECORATORS ##################################################### DECORATORS #
###############################################################################


def verify_proceed(func):
    """Decorator for verifying that the file is not cancelled.
    Also cancels the upload of all non-started files if break-on-fail."""

    @functools.wraps(func)
    def wrapped(self, file, *args, **kwargs):

        # Return if file cancelled by another file
        if self.status[file]["cancel"]:
            message = f"File already cancelled, stopping file {file}"
            LOG.warning(message)
            return False

        # Run function
        ok_to_proceed, message = func(self, file=file, *args, **kwargs)

        # Cancel file(s) if something failed
        if not ok_to_proceed:
            self.status[file].update({"cancel": True, "message": message})
            if self.break_on_fail:
                message = (
                    f"Cancelling upload due to file '{file}'. "
                    "Break-on-fail specified in call."
                )

                _ = [
                    self.status[x].update({"cancel": True, "message": message})
                    for x in self.status
                    if not self.status[x]["cancel"]
                    and not self.status[x]["started"]
                    and x != file
                ]

        return ok_to_proceed

    return wrapped


def update_status(func):
    """Decorator for updating the status of files."""

    @functools.wraps(func)
    def wrapped(self, file, *args, **kwargs):

        if func.__name__ not in ["put", "add_file_db", "get", "update_db"]:
            raise Exception(
                f"The function {func.__name__} cannot be used with this decorator."
            )
        if func.__name__ not in self.status[file]:
            raise Exception(f"No status found for function {func.__name__}.")

        # Update status to started
        self.status[file][func.__name__].update({"started": True})

        # Run function
        ok_to_continue, message, *_ = func(self, file=file, *args, **kwargs)

        if not ok_to_continue:
            return False, message

        # Update status to done
        self.status[file][func.__name__].update({"done": True})

        return ok_to_continue, message

    return wrapped


def connect_cloud(func):
    """Connect to S3"""

    @functools.wraps(func)
    def init_resource(self, *args, **kwargs):

        # Connect to service
        try:
            session = boto3.session.Session()

            self.resource = session.resource(
                service_name="s3",
                endpoint_url=self.url,
                aws_access_key_id=self.keys["access_key"],
                aws_secret_access_key=self.keys["secret_key"],
            )
        except botocore.client.ClientError as err:
            self.url, self.keys, self.message = (
                None,
                None,
                f"S3 connection failed: {err}",
            )
        else:
            return func(self, *args, **kwargs)

    return init_resource


def subpath_required(func):
    """Make sure that the subpath to the downloaded files exist."""

    @functools.wraps(func)
    def check_and_create(self, *args, **kwargs):

        # Check that function has correct args
        if "file" not in kwargs:
            raise Exception(
                "Missing key word argument in wrapper over "
                f"function {func.__name__}: 'file'"
            )
        file = kwargs["file"]

        file_info = self.filehandler.data[file]
        full_subpath = self.filehandler.destination / pathlib.Path(file_info["subpath"])

        if not full_subpath.exists():
            try:
                full_subpath.mkdir(parents=True, exist_ok=True)
            except Exception as err:
                return False, str(err)

        return func(self, *args, **kwargs)

    return check_and_create