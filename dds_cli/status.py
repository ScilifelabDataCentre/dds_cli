"""Status module"""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import logging
import threading
import os
import itertools

# Installed
from rich.progress import (
    Progress,
    TextColumn,
    BarColumn,
    DownloadColumn,
    SpinnerColumn,
    Column,
    Table,
)
from rich.panel import Panel
import boto3

# Own modules

###############################################################################
# START LOGGING CONFIG ################################# START LOGGING CONFIG #
###############################################################################

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)

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
    """Progress bar formatting."""

    LOG.debug("Progress bar created.")

    # def get_renderables(self):
    #     """Get a number of renderables for the progress display."""
    #     yield self.make_tasks_table(self.tasks)

    # def make_tasks_table(self, tasks):
    #     """Get a table to render the Progress display.

    #     Args:
    #         tasks (Iterable[Task]): An iterable of Task instances, one per row of the table.

    #     Returns:
    #         Table: A table instance.
    #     """

    #     table_columns = (
    #         (
    #             Column(no_wrap=True)
    #             if isinstance(_column, str)
    #             else _column.get_table_column().copy()
    #         )
    #         for _column in self.columns
    #     )
    #     table = Table.grid(*table_columns, padding=(0, 1), expand=self.expand)

    #     for task in tasks:
    #         if task.visible:
    #             table.add_row(
    #                 *(
    #                     (
    #                         column.format(task=task)
    #                         if isinstance(column, str)
    #                         else column(task)
    #                     )
    #                     for column in self.columns
    #                 )
    #             )

    #     return table

    # def get_renderables(self):

    # table = self.make_tasks_table([task])
    # yield table

    # for task in self.tasks:
    #     step = task.fields.get("step")
    #     if step == "prepare":
    #         self.columns = (
    #             "[bold]{task.description}",
    #             SpinnerColumn(spinner_name="dots12", style="white"),
    #         )
    #     elif step == "summary":
    #         self.columns = (
    #             TextColumn(task.description, style="bold cyan"),
    #             BarColumn(
    #                 bar_width=None,
    #                 complete_style="bold cyan",
    #                 finished_style="bold cyan",
    #             ),
    #             " • ",
    #             "[green]{task.completed}/{task.total} completed",
    #         )
    #     elif step in ["put", "get", "encrypt", "decrypt"]:
    #         symbol = ""
    #         if step == "put":
    #             symbol = ":arrow_up:"
    #         elif step == "get":
    #             symbol = ":arrow_down:"
    #         elif step == "encrypt":
    #             symbol = ":lock:"

    #         self.columns = (
    #             symbol,
    #             TextColumn(task.description),
    #             BarColumn(
    #                 bar_width=None,
    #                 complete_style="bold white",
    #                 finished_style="bold white",
    #             ),
    #             "•",
    #             "[progress.percentage]{task.percentage:>3.1f}%",
    #             "•",
    #             DownloadColumn(),
    #         )
    #     elif task.fields.get("step") == "db":
    #         self.columns = (
    #             SpinnerColumn(spinner_name="dots"),
    #             TextColumn(task.description),
    #         )

    #     yield self.make_tasks_table([task])


class ProgressPercentage(object):
    """Updates the progress bar with the callback from boto3."""

    def __init__(self, progress, task):
        self.progress = progress
        self.task = task

        self._seen_so_far = 0

    def __call__(self, bytes_amount, **_):

        self._seen_so_far += bytes_amount
        self.progress.update(self.task, advance=bytes_amount)
