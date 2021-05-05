"""Data Lister -- Lists the projects and project content."""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import logging
import pathlib
import traceback
import sys
import os

# Installed
import requests
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt
from rich.tree import Tree
from rich.padding import Padding
import simplejson

# Own modules
from dds_cli import text_handler as th
from dds_cli import base
from dds_cli import DDSEndpoint

###############################################################################
# START LOGGING CONFIG ################################# START LOGGING CONFIG #
###############################################################################

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)

###############################################################################
# RICH ################################################################# RICH #
###############################################################################

###############################################################################
# CLASSES ########################################################### CLASSES #
###############################################################################


class DataLister(base.DDSBaseClass):
    """Data lister class."""

    def __init__(
        self,
        username: str = None,
        config: pathlib.Path = None,
        project: str = None,
        project_level: bool = False,
    ):

        # Initiate DDSBaseClass to authenticate user
        super().__init__(
            username=username,
            config=config,
            project=project,
            ignore_config_project=project_level,
        )

        # Only method "ls" can use the DataLister class
        if self.method != "ls":
            sys.exit(f"Unauthorized method: {self.method}")

    # Static methods ########################### Static methods #
    @staticmethod
    def warn_if_many(count, threshold=50):
        """Warn the user if there are many lines to print out."""

        if count > threshold:
            do_continue = Prompt.ask(
                f"\nItems to display: {count}. "
                "The display layout might be affected due to too many entries."
                f"\nTip: Try the command again with [b]| more[/b] at the end."
                "\n\nContinue anyway?",
                choices=["y", "n"],
                default="n",
            )

            if not do_continue in ["y", "yes"]:
                os._exit(0)

    # Public methods ########################### Public methods #
    def list_projects(self):
        """Gets a list of all projects the user is involved in."""

        # Get projects from API
        try:
            response = requests.get(DDSEndpoint.LIST_PROJ, headers=self.token)
        except requests.exceptions.RequestException as err:
            raise SystemExit from err

        console = Console()
        if not response.ok:
            console.print(f"Failed to get list of projects: {response.text}")
            os._exit(0)

        try:
            resp_json = response.json()
            LOG.warning(resp_json)
        except simplejson.JSONDecodeError as err:
            raise SystemExit from err

        # Cancel if user not involved in any projects
        if "all_projects" not in resp_json:
            console.print("No project info was retrieved. No files to list.")
            os._exit(0)

        # Warn user if many lines to print
        self.warn_if_many(count=len(resp_json["all_projects"]))

        # Sort list of projects by 1. Last updated, 2. Project ID
        sorted_projects = sorted(
            sorted(resp_json["all_projects"], key=lambda i: i["Project ID"]),
            key=lambda t: (t["Last updated"] is None, t["Last updated"]),
            reverse=True,
        )

        # Create table
        table = Table(title="Your Projects", show_header=True, header_style="bold")

        # Add columns to table
        columns = resp_json["columns"]
        for col in columns:
            just = "left"
            if col == "Last updated":
                just = "center"

            style = None
            if "ID" in col:
                style = "green"
            table.add_column(col, justify=just, style=style)

        # Add all column values for each row to table
        for proj in sorted_projects:
            table.add_row(*[proj[columns[i]] for i in range(len(columns))])

        # Print if there are any lines
        if table.columns:
            console.print(table)
        else:
            console.print("[i]No projects[/i]")

    def list_files(self, folder: str = None, show_size: bool = False):
        """Create a tree displaying the files within the project."""

        console = Console()

        # Make call to API
        try:
            response = requests.get(
                DDSEndpoint.LIST_FILES,
                params={"subpath": folder, "show_size": show_size},
                headers=self.token,
            )
        except requests.exceptions.RequestException as err:
            raise SystemExit from err

        if not response.ok:
            console.print(f"Failed to get list of files: {response.text}")
            os._exit(0)

        # Get response
        try:
            resp_json = response.json()
        except simplejson.JSONDecodeError as err:
            raise SystemExit from err

        # Check if project empty
        if "num_items" in resp_json and resp_json["num_items"] == 0:
            console.print(f"[i]Project '{self.project}' is empty.[/i]")
            os._exit(0)

        # Get files
        files_folders = resp_json["files_folders"]

        # Warn user if there will be too many rows
        self.warn_if_many(count=len(files_folders))

        # Sort the file/folders according to names
        sorted_projects = sorted(files_folders, key=lambda f: f["name"])

        # Create tree
        tree_title = folder
        if folder is None:
            tree_title = f"Files/Directories in project: {self.project}"
        tree = Tree(f"[bold spring_green4]{tree_title}")

        if sorted_projects:
            # Get max length of file name
            max_string = max([len(x["name"]) for x in sorted_projects])

            # Get max length of size string
            sizes = [len(x["size"][0]) for x in sorted_projects if show_size and "size" in x]
            max_size = max(sizes) if sizes else 0

            # Add items to tree
            for x in sorted_projects:
                # Check if string is folder
                is_folder = x.pop("folder")

                # Att 1 for folders due to trailing /
                tab = th.TextHandler.format_tabs(
                    string_len=len(x["name"]) + (1 if is_folder else 0),
                    max_string_len=max_string,
                )

                # Add formatting if folder and set string name
                line = ""
                if is_folder:
                    line = "[bold deep_sky_blue3]"
                line += x["name"] + ("/" if is_folder else "")

                # Add size to line if option specified
                if show_size and "size" in x:
                    line += f"{tab}{x['size'][0]}"

                    # Define space between number and size format
                    tabs_bf_format = th.TextHandler.format_tabs(
                        string_len=len(x["size"][0]), max_string_len=max_size, tab_len=2
                    )
                    line += f"{tabs_bf_format}{x['size'][1]}"
                tree.add(line)
            console.print(Padding(tree, 1))
        else:
            console.print(Padding(f"[i]No folder called '{folder}'[/i]", 1))
