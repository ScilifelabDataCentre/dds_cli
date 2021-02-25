"""Data Lister -- Lists the projects and project content."""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import dataclasses
import logging
import pathlib
import traceback
import sys

# Installed
import requests
from rich.console import Console
from rich.table import Column, Table

# Own modules
from cli_code import file_handler as fh
from cli_code import user
from cli_code import base
from cli_code import DDSEndpoint

###############################################################################
# START LOGGING CONFIG ################################# START LOGGING CONFIG #
###############################################################################

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

###############################################################################
# DECORATORS ##################################################### DECORATORS #
###############################################################################

###############################################################################
# CLASSES ########################################################### CLASSES #
###############################################################################


@dataclasses.dataclass
class DataLister(base.DDSBaseClass):
    """Data lister class."""

    def __init__(self, username: str = None, config: pathlib.Path = None,
                 project: str = None):

        # Initiate DDSBaseClass to authenticate user
        super().__init__(username=username, config=config, project=project)

        # Only method "ls" can use the DataLister class
        if self.method != "ls":
            sys.exit(f"Unauthorized method: {self.method}")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if exc_type is not None:
            traceback.print_exception(exc_type, exc_value, tb)
            return False  # uncomment to pass exception through

        return True

    # Public methods ########################### Public methods #
    def list_projects(self):
        """Gets a list of all projects the user is involved in."""

        import operator
        response = requests.get(DDSEndpoint.LIST_PROJ, headers=self.token)

        if not response.ok:
            sys.exit("Failed to get list of projects. "
                     f"{response.status_code} -- {response.text}")

        resp_json = response.json()
        if "all_projects" not in resp_json:
            sys.exit("No project info was retrieved. No files to list.")

        sorted_projects = sorted(
            sorted(resp_json["all_projects"],
                   key=lambda i: i["Project ID"]
                   ),
            key=lambda t: (t["Last updated"] is None, t["Last updated"]),
            reverse=True
        )

        console = Console()
        table = Table(show_header=True, header_style="bold magenta")

        columns = resp_json["columns"]
        for col in columns:
            table.add_column(col)

        # Add all column values for each row to table
        for proj in sorted_projects:
            table.add_row(
                *[proj[columns[i]] for i in range(len(columns))]
            )

        console.print(table)
