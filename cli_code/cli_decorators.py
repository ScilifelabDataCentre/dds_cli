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
import hashlib
import base64

# Installed
import boto3
import botocore
import rich
from rich.progress import Progress, TextColumn, BarColumn, DownloadColumn, SpinnerColumn

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


def generate_checksum(func):
    @functools.wraps(func)
    def gen_hash(self, file, raw_file, *args, **kwargs):

        checksum = hashlib.sha256()

        for chunk in func(self, file=raw_file, *args, **kwargs):
            checksum.update(chunk)
            yield chunk

        self.data[file]["checksum"] = checksum.hexdigest()

    return gen_hash


def checksum_verification_required(func):
    @functools.wraps(func)
    def verify_checksum(correct_checksum, do_verify: bool = False, *args, **kwargs):

        done, message = (False, "")
        try:
            chunks = func(*args, **kwargs)

            if do_verify:
                checksum = hashlib.sha256()
                try:
                    for chunk in chunks:
                        checksum.update(chunk)
                except Exception as cs_err:
                    message = str(cs_err)
                    LOG.exception(message)
                else:
                    checksum_digest = checksum.hexdigest()
                    LOG.debug(
                        "Correct checksum: %s\nChecksum of downloaded file: %s\nCorrect? %s",
                        correct_checksum,
                        checksum_digest,
                        correct_checksum == checksum_digest,
                    )

                    if checksum_digest != correct_checksum:
                        message = "Checksum verification failed. File compromised."
                    else:
                        done = True
        except Exception as err:
            message = str(err)
            LOG.exception(message)
        else:
            done = True

        return done, message

    return verify_checksum


def verify_proceed(func):
    """Decorator for verifying that the file is not cancelled.
    Also cancels the upload of all non-started files if break-on-fail."""

    @functools.wraps(func)
    def wrapped(self, file, *args, **kwargs):

        if self.stop_doing:
            message = "KeyBoardInterrupt - cancelling file {file}"
            LOG.warning(message)
            return False

        # Return if file cancelled by another file
        if self.status[file]["cancel"]:
            message = f"File already cancelled, stopping file {file}"
            LOG.warning(message)
            return False

        self.status[file]["started"] = True

        # Run function
        ok_to_proceed, message = func(self, file=file, *args, **kwargs)

        # Cancel file(s) if something failed
        if ok_to_proceed:
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
        except Exception as err:
            # except botocore.client.ClientError as err:
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
    def check_and_create(self, file, *args, **kwargs):

        file_info = self.filehandler.data[file]
        full_subpath = self.filehandler.local_destination / pathlib.Path(
            file_info["subpath"]
        )

        if not full_subpath.exists():
            try:
                full_subpath.mkdir(parents=True, exist_ok=True)
            except Exception as err:
                return False, str(err)

        return func(self, file=file, *args, **kwargs)

    return check_and_create


def removal_spinner(func):
    @functools.wraps(func)
    def create_and_remove_task(self, *args, **kwargs):
        message = ""
        with Progress(
            "[bold]{task.description}",
            SpinnerColumn(spinner_name="dots12", style="white"),
        ) as progress:

            if func.__name__ == "remove_all":
                description = f"Removing all files in project {self.project}..."
            elif func.__name__ == "remove_file":
                description = "Removing file(s)..."
            elif func.__name__ == "remove_folder":
                description = "Removing folder(s)..."

            task = progress.add_task(description=description)

            message = func(self, *args, **kwargs)

            progress.remove_task(task)

        console = rich.console.Console()
        console.print(message)

    return create_and_remove_task
