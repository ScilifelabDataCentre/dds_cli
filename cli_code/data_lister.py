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

# Own modules
from cli_code import text_handler as th
from cli_code import base
from cli_code import DDSEndpoint

###############################################################################
# START LOGGING CONFIG ################################# START LOGGING CONFIG #
###############################################################################

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

###############################################################################
# RICH ################################################################# RICH #
###############################################################################

###############################################################################
# CLASSES ########################################################### CLASSES #
###############################################################################


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

    # Static methods ########################### Static methods #
    @staticmethod
    def __warn_if_many(count, threshold=50):
        """Warn the user if there are many lines to print out."""

        if count > threshold:
            do_continue = Prompt.ask(
                f"\nItems to list: {count}. "
                "The display layout might be affected due to too many entries."
                f"\nTip: Try the command again with [b]| more[/b] at the end."
                "\n\nContinue anyway?", choices=["y", "n"], default="n"
            )

            if not do_continue in ["y", "yes"]:
                print("\nCancelled listing function.\n")
                os._exit(os.EX_OK)

    # Public methods ########################### Public methods #
    def list_projects(self):
        """Gets a list of all projects the user is involved in."""

        # Get projects from API
        response = requests.get(DDSEndpoint.LIST_PROJ, headers=self.token)

        if not response.ok:
            sys.exit("Failed to get list of projects. "
                     f"{response.status_code} -- {response.text}")

        resp_json = response.json()

        # Cancel if user not involved in any projects
        if "all_projects" not in resp_json:
            sys.exit("No project info was retrieved. No files to list.")

        # Warn user if many lines to print
        self.__warn_if_many(count=len(resp_json["all_projects"]))

        # Sort list of projects by 1. Last updated, 2. Project ID
        sorted_projects = sorted(
            sorted(resp_json["all_projects"],
                   key=lambda i: i["Project ID"]
                   ),
            key=lambda t: (t["Last updated"] is None, t["Last updated"]),
            reverse=True
        )

        # Create table
        console = Console()
        table = Table(title="Your Projects", show_header=True,
                      header_style="bold")

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
            table.add_row(
                *[proj[columns[i]] for i in range(len(columns))]
            )

        # Print if there are any lines
        if table.columns:
            console.print(table)
        else:
            console.print("[i]No projects[/i]")

    def list_files(self, folder: str = None, show_size: bool = False):
        """Create a tree displaying the files within the project."""
        
        console = Console()

        # Make call to API
        response = requests.get(DDSEndpoint.LIST_FILES,
                                params={"subpath": folder,
                                        "show_size": show_size},
                                headers=self.token)
        if not response.ok:
            sys.exit("Failed to get list of files. "
                     f"{response.status_code} -- {response.text}")

        # Get response
        resp_json = response.json()
        
        # Check if project empty
        if "num_items" in resp_json and resp_json["num_items"] == 0:
            console.print(f"[i]Project '{self.project}' is empty.[/i]")
            return

        # Get files
        files_folders = resp_json["files_folders"]

        # Warn user if there will be too many rows
        self.__warn_if_many(count=len(files_folders))

        # Sort the file/folders according to names
        sorted_projects = sorted(files_folders,
                                key=lambda f: f["name"])

        # Create tree
        tree_title = folder
        if folder is None:
            tree_title = f"Files/Directories in project: {self.project}"
        tree = Tree(f"[bold spring_green4]{tree_title}")

        if sorted_projects:
            # Get max length of file name
            max_string = max([len(x["name"]) for x in sorted_projects])

            # Get max length of size string
            sizes = [len(x["size"][0]) for x in sorted_projects
                    if show_size and "size" in x]
            max_size = max(sizes) if sizes else 0

            # Add items to tree
            for x in sorted_projects:
                # Check if string is folder
                is_folder = x.pop("folder")

                # Att 1 for folders due to trailing /
                tab = th.TextHandler.format_tabs(
                    string_len=len(x["name"])+(1 if is_folder else 0),
                    max_string_len=max_string
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
                        string_len=len(x["size"][0]),
                        max_string_len=max_size,
                        tab_len=2
                    )
                    line += f"{tabs_bf_format}{x['size'][1]}"
                tree.add(line)
            console.print(tree)
        else:
            console.print(f"[i]No folder called '{folder}'[/i]")
