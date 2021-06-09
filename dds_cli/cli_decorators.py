"""Module for all decorators related to the execution of the DDS CLI."""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import functools
import logging
import pathlib

# Installed
import boto3
import botocore
import rich
from rich.progress import Progress, SpinnerColumn

# Own modules

###############################################################################
# START LOGGING CONFIG ################################# START LOGGING CONFIG #
###############################################################################

LOG = logging.getLogger(__name__)

###############################################################################
# DECORATORS ##################################################### DECORATORS #
###############################################################################


def verify_proceed(func):
    """Decorator for verifying that the file is not cancelled.
    Also cancels the upload of all non-started files if break-on-fail."""

    @functools.wraps(func)
    def wrapped(self, file, *args, **kwargs):

        # Check if keyboardinterrupt in dds
        if self.stop_doing:
            # TODO (ina): Add save to status here
            message = "KeyBoardInterrupt - cancelling file {file}"
            LOG.warning(message)
            return False  # Do not proceed

        # Return if file cancelled by another file
        if self.status[file]["cancel"]:
            message = f"File already cancelled, stopping file {file}"
            LOG.warning(message)
            return False

        # Mark as started
        self.status[file]["started"] = True
        LOG.info(f"File {file} started {func.__name__}")

        # Run function
        ok_to_proceed, message = func(self, file=file, *args, **kwargs)

        # Cancel file(s) if something failed
        if not ok_to_proceed:
            LOG.warning(f"{func.__name__} failed: {message}")
            self.status[file].update({"cancel": True, "message": message})
            if self.status[file].get("failed_op") is None:
                self.status[file]["failed_op"] = "crypto"

            if self.break_on_fail:
                message = f"'--break-on-fail'. File causing failure: '{file}'. "
                LOG.info(message)

                _ = [
                    self.status[x].update({"cancel": True, "message": message})
                    for x in self.status
                    if not self.status[x]["cancel"] and not self.status[x]["started"] and x != file
                ]

        return ok_to_proceed

    return wrapped


def update_status(func):
    """Decorator for updating the status of files."""

    @functools.wraps(func)
    def wrapped(self, file, *args, **kwargs):

        # TODO (ina): add processing?
        if func.__name__ not in ["put", "add_file_db", "get", "update_db"]:
            raise Exception(f"The function {func.__name__} cannot be used with this decorator.")
        if func.__name__ not in self.status[file]:
            raise Exception(f"No status found for function {func.__name__}.")

        # Update status to started
        self.status[file][func.__name__].update({"started": True})
        LOG.debug(f"File {file} status updated to {func.__name__}: started")

        # Run function
        ok_to_continue, message, *_ = func(self, file=file, *args, **kwargs)

        # ok_to_continue = False
        if not ok_to_continue:
            # Save info about which operation failed
            self.status[file]["failed_op"] = func.__name__
            LOG.warning(f"{func.__name__} failed: {message}")

        else:
            # Update status to done
            self.status[file][func.__name__].update({"done": True})
            LOG.debug(f"File {file} status updated to {func.__name__}: done")

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
        except (boto3.exceptions.Boto3Error, botocore.exceptions.BotoCoreError) as err:
            self.url, self.keys, self.message = (
                None,
                None,
                f"S3 connection failed: {err}",
            )
        else:
            LOG.debug("Connection to S3 established.")
            return func(self, *args, **kwargs)

    return init_resource


def subpath_required(func):
    """Make sure that the subpath to the temporary file directory exist."""

    @functools.wraps(func)
    def check_and_create(self, file, *args, **kwargs):
        """Create the sub directory if it does not exist."""

        file_info = self.filehandler.data[file]

        # Required path
        full_subpath = self.filehandler.local_destination / pathlib.Path(file_info["subpath"])

        # Create path
        if not full_subpath.exists():
            try:
                full_subpath.mkdir(parents=True, exist_ok=True)
            except OSError as err:
                return False, str(err)

            LOG.info(f"New directory created: {full_subpath}")

        return func(self, file=file, *args, **kwargs)

    return check_and_create


def removal_spinner(func):
    """Spinner for the rm command"""

    @functools.wraps(func)
    def create_and_remove_task(self, *args, **kwargs):

        message = ""

        with Progress(
            "[bold]{task.description}",
            SpinnerColumn(spinner_name="dots12", style="white"),
        ) as progress:

            # Determine spinner text
            if func.__name__ == "remove_all":
                description = f"Removing all files in project {self.project}..."
            elif func.__name__ == "remove_file":
                description = "Removing file(s)..."
            elif func.__name__ == "remove_folder":
                description = "Removing folder(s)..."

            # Add progress task
            task = progress.add_task(description=description)

            # Execute function
            message = func(self, *args, **kwargs)

            # Remove progress task
            progress.remove_task(task)

        # Printout removal response
        if message is None:
            rm_type = "File" if func.__name__ == "remove_file" else "Folder"

            message = f"{rm_type}(s) successfully removed."

        console = rich.console.Console()
        console.print(message)

    return create_and_remove_task
