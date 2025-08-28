"""Module for all decorators related to the execution of the DDS CLI."""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import functools
import logging
import pathlib

# Installed
from rich.markup import escape
from rich.progress import Progress, SpinnerColumn

# Own modules
import dds_cli
import dds_cli.utils
import dds_cli.file_handler

###############################################################################
# START LOGGING CONFIG ################################# START LOGGING CONFIG #
###############################################################################

LOG = logging.getLogger(__name__)

###############################################################################
# DECORATORS ##################################################### DECORATORS #
###############################################################################


def verify_proceed(func):
    """Verify that the file is not cancelled.

    Also cancels the upload of all non-started files if break-on-fail.
    """

    @functools.wraps(func)
    def wrapped(self, file, *args, **kwargs):
        # Check if keyboardinterrupt in dds
        if self.stop_doing:
            # TODO (ina): Add save to status here
            message = f"KeyboardInterrupt - cancelling file {escape(file)}"
            LOG.warning(message)
            return False  # Do not proceed

        # Return if file cancelled by another file
        if self.status[file]["cancel"]:
            message = f"File already cancelled, stopping file {escape(file)}"
            LOG.warning(message)
            return False

        # Mark as started
        self.status[file]["started"] = True

        # Run function
        ok_to_proceed, message = func(self, file=file, *args, **kwargs)
        # Cancel file(s) if something failed
        if not ok_to_proceed:
            LOG.warning("%s failed: %s", func.__name__, message)
            self.status[file].update({"cancel": True, "message": message})
            if self.status[file].get("failed_op") is None:
                self.status[file]["failed_op"] = "crypto"

            if self.break_on_fail:
                message = f"'--break-on-fail'. File causing failure: '{file}'. "
                LOG.warning(message)

                _ = [
                    self.status[x].update({"cancel": True, "message": message})
                    for x in self.status
                    if not self.status[x]["cancel"] and not self.status[x]["started"] and x != file
                ]

            dds_cli.file_handler.FileHandler.append_errors_to_file(
                log_file=self.failed_delivery_log,
                file=file,
                info=self.filehandler.data[file],
                status=self.status[file],
            )
        return ok_to_proceed

    return wrapped


def update_status(func):
    """Decorator for updating the status of files."""

    @functools.wraps(func)
    def wrapped(self, file, *args, **kwargs):
        # TODO (ina): add processing?
        if func.__name__ not in ["put", "add_file_db", "get", "update_db"]:
            raise dds_cli.exceptions.DDSCLIException(
                f"The function {func.__name__} cannot be used with this decorator."
            )
        if func.__name__ not in self.status[file]:
            raise dds_cli.exceptions.DDSCLIException(
                f"No status found for function {func.__name__}."
            )

        # Update status to started
        self.status[file][func.__name__].update({"started": True})

        # Run function
        ok_to_continue, message, *_ = func(self, file=file, *args, **kwargs)

        # ok_to_continue = False
        if not ok_to_continue:
            # Save info about which operation failed
            self.status[file]["failed_op"] = func.__name__
            LOG.warning("%s failed: %s", func.__name__, message)

        else:
            # Update status to done
            self.status[file][func.__name__].update({"done": True})

        return ok_to_continue, message

    return wrapped


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

            LOG.debug("New directory created: '%s'", full_subpath)

        return func(self, file=file, *args, **kwargs)

    return check_and_create


def removal_spinner(func):
    """Spinner for the rm command"""

    @functools.wraps(func)
    def create_and_remove_task(self, *args, **kwargs):
        with Progress(
            "[bold]{task.description}",
            SpinnerColumn(spinner_name="dots12", style="white"),
            console=dds_cli.utils.stderr_console,
        ) as progress:
            # Determine spinner text
            if func.__name__ == "remove_all":
                description = f"Removing all files in project {self.project}"
            elif func.__name__ == "remove_file":
                description = "Removing file(s)"
            elif func.__name__ == "remove_folder":
                description = "Removing folder(s)"

            # Add progress task
            task = progress.add_task(description=f"{description}...")

            # Execute function, exceptions are caught in __main__.py
            try:
                func(self, *args, **kwargs)
            finally:
                # Remove progress task
                progress.remove_task(task)

        # Printout removal response

        # reuse the description but don't want the capital letter in the middle of the sentence.
        description_lc = description[0].lower() + description[1:]
        if self.failed_table is not None:
            table_len = self.failed_table.renderable.row_count

            if table_len + 5 > dds_cli.utils.console.height:
                with dds_cli.utils.console.pager():
                    dds_cli.utils.console.print(self.failed_table)
            else:
                dds_cli.utils.console.print(self.failed_table)
            LOG.warning("Finished %s with errors, see table above", description_lc)
        elif self.failed_files is not None:
            self.failed_files["result"] = f"Finished {description_lc} with errors"
            dds_cli.utils.console.print(self.failed_files)
        else:
            dds_cli.utils.console.print(f"Successfully finished {description_lc}")

    return create_and_remove_task
