"""Status module"""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import logging
import threading

# Installed
from rich.progress import Progress, TextColumn, BarColumn, DownloadColumn

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
            if task.fields.get("progress_type") == "upload":
                self.columns = (
                    TextColumn("[bold]{task.description}"),
                    BarColumn(bar_width=None),
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
