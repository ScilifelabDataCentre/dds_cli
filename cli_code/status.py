"""Status module"""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import logging
import threading

# Installed

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


class ProgressTasks:

    TASKS = {}

    def add_task(self, path_name, task_size):

        self.TASKS[path_name] = {"task": None, "total": task_size}


class ProgressPercentage(object):
    def __init__(self, ud_file_size, progress, task):
        self.progress = progress
        self.task = task
        # self._filename = filename
        self._size = ud_file_size
        self._seen_so_far = 0
        # self._download = get
        self._lock = threading.Lock()
        # print(f"\n\n\n\n\n{self._filename}\n\n\n\n\n")

    def __call__(self, bytes_amount):
        # To simplify, assume this is hooked up to a single filename
        with self._lock:
            self._seen_so_far += bytes_amount
            percentage = (self._seen_so_far / self._size) * 100
            # print(self._filename, percentage)

            self.progress.update(self.task, advance=bytes_amount)
            # update_progress_bar(
            #     file=self._filename,
            #     status="d" if self._download else "u",
            #     perc=percentage,
            # )
