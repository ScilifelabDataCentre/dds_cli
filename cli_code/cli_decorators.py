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
    def wrapped(self, *args, **kwargs):

        # Check that function has correct args
        if "file" not in kwargs:
            raise Exception(
                "Missing key word argument in wrapper over "
                f"function {func.__name__}: 'file'"
            )
        file = kwargs["file"]

        # Return if file cancelled by another file
        if self.status[file]["cancel"]:
            message = f"File already cancelled, stopping file {file}"
            LOG.warning(message)
            return False

        # Run function
        ok_to_proceed, message = func(self, *args, **kwargs)

        # Cancel file(s) if something failed
        if not ok_to_proceed:
            # TODO (ina): update progress bar -- e.g. folder, change total size?
            self.status[file].update({"cancel": True, "message": message})
            if self.break_on_fail:
                message = (
                    f"Cancelling upload due to file '{file}'. "
                    "Break-on-fail specified in call."
                )

                put_or_get = "put" if "put" in self.status[file] else "get"
                _ = [
                    self.status[x].update({"cancel": True, "message": message})
                    for x in self.status
                    if not self.status[x]["cancel"]
                    and not any(
                        [
                            self.status[x][put_or_get]["started"],
                            self.status[x][put_or_get]["done"],
                        ]
                    )
                    and x != file
                ]

        return ok_to_proceed

    return wrapped


def update_status(func):
    """Decorator for updating the status of files."""

    @functools.wraps(func)
    def wrapped(self, *args, **kwargs):

        # Check that function has correct args
        if "file" not in kwargs:
            raise Exception(
                "Missing key word argument in wrapper over "
                f"function {func.__name__}: 'file'"
            )
        file = kwargs["file"]

        if func.__name__ not in ["put", "add_file_db", "get", "update_db"]:
            raise Exception(
                f"The function {func.__name__} cannot be used with this decorator."
            )
        if func.__name__ not in self.status[file]:
            raise Exception(f"No status found for function {func.__name__}.")

        # Update status to started
        self.status[file][func.__name__].update({"started": True})

        # Run function
        ok_to_continue, message, *_ = func(self, *args, **kwargs)

        if not ok_to_continue:
            return False, message

        # Update status to done
        self.status[file][func.__name__].update({"done": True})

        return ok_to_continue, message

    return wrapped


def progress_bar(func):
    """Decorator for handling the progress bars"""

    @functools.wraps(func)
    def start_and_cancel(self, *args, **kwargs):

        file = kwargs["file"]

        if "progress" not in kwargs:
            return False, "Missing progress object when attempting to add task."

        progress = kwargs["progress"]

        task_name = file
        if len(file) > 30:
            # print(len(file))
            file_name = pathlib.Path(file).name
            task_name = f".../{file_name}"
            if len(task_name) > 30:
                # print(len(task_name))
                task_name = "..." + task_name.split("...", 1)[-1][-30::]

        task = progress.add_task(
            task_name,
            total=self.filehandler.data[file]["size"],
            progress_type=func.__name__,
        )

        ok_to_continue, message, *_ = func(self, task=task, *args, **kwargs)

        progress.remove_task(task)

        return ok_to_continue, message

    return start_and_cancel


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
        LOG.debug(full_subpath)
        if not full_subpath.exists():
            try:
                full_subpath.mkdir(parents=True, exist_ok=True)
            except Exception as err:
                return False, str(err)

        return func(self, *args, **kwargs)

    return check_and_create