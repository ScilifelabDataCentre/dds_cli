"""Status module"""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import logging
import threading
import os

# Installed
from rich.progress import Progress, TextColumn, BarColumn, DownloadColumn, SpinnerColumn

# Own modules

###############################################################################
# START LOGGING CONFIG ################################# START LOGGING CONFIG #
###############################################################################

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

###############################################################################
# CLASSES ########################################################### CLASSES #
###############################################################################


class DeliveryStatus:

    UPLOAD_STATUS = {
        "upload": {"in_progress": False, "finished": False},
        "processing": {"in_progress": False, "finished": False},
        "database": {"in_progress": False, "finished": False},
    }

    @classmethod
    def cancel_all(cls):
        """Cancel upload all files"""

    @classmethod
    def cancel_one(cls):
        """Cancel the failed file"""


class DeliveryProgress(Progress):
    def get_renderables(self):
        for task in self.tasks:
            if task.fields.get("progress_type") == "wait":
                self.columns = (
                    "[bold]{task.description}",
                    SpinnerColumn(spinner_name="shark"),
                )
            if task.fields.get("progress_type") == "summary":
                self.columns = (
                    "[bold red]{task.description}",
                    BarColumn(bar_width=None, finished_style="bar.complete"),
                    "[progress.percentage]{task.percentage:>3.0f}%",
                    "•",
                    "[green]{task.completed}/{task.total} completed",
                )
            if task.fields.get("progress_type") == "put":
                self.columns = (
                    ":arrow_up:",
                    TextColumn(task.description),
                    BarColumn(
                        bar_width=None,
                        complete_style="bold cyan",
                        finished_style="bold cyan",
                    ),
                    "[progress.percentage]{task.percentage:>3.1f}%",
                    "•",
                    DownloadColumn(),
                )

            yield self.make_tasks_table([task])


class ProgressPercentage(object):
    def __init__(self, filename, ud_file_size, progress, task):
        self.filename = filename
        self.progress = progress
        self.task = task
        self._size = ud_file_size
        self._seen_so_far = 0

    def __call__(self, bytes_amount):

        self._seen_so_far += bytes_amount
        # percentage = (self._seen_so_far / self._size) * 100

        self.progress.update(self.task, advance=bytes_amount)
