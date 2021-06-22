"""Data Lister -- Lists the projects and project content."""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import logging
import pathlib

# Installed
import requests
import simplejson
from rich.console import Console
from rich.padding import Padding
from rich.table import Table
from rich.tree import Tree

# Own modules
from dds_cli import base
from dds_cli import exceptions
from dds_cli import DDSEndpoint
from dds_cli import text_handler as th

###############################################################################
# START LOGGING CONFIG ################################# START LOGGING CONFIG #
###############################################################################

LOG = logging.getLogger(__name__)

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
        show_usage: bool = False,
    ):

        # Initiate DDSBaseClass to authenticate user
        super().__init__(
            username=username,
            config=config,
            project=project,
        )

        # Only method "ls" can use the DataLister class
        if self.method != "ls":
            raise exceptions.AuthenticationError(f"Unauthorized method: '{self.method}'")

        self.show_usage = show_usage

    # Public methods ########################### Public methods #
    def _show_usage(self):
        """Get the usage for a specific facility"""

        # Call API endpoint to calculate usage
        try:
            response = requests.get(DDSEndpoint.USAGE, headers=self.token)
        except requests.exceptions.RequestException as err:
            raise exceptions.APIError(f"Problem with database response: {err}")

        # Check that request ok
        if not response.ok:
            raise exceptions.APIError(f"Failed to get calculated usage and cost: {response.text}")

        # Get json resposne
        try:
            resp_json = response.json()
            project_usage = resp_json["project_usage"]
            total_usage = resp_json["total_usage"]
        except simplejson.JSONDecodeError as err:
            raise exceptions.APIError(f"Could not decode JSON response: {err}")

        LOG.debug(resp_json)

        # Sort projects according to id
        sorted_projects = sorted(project_usage, key=lambda i: i)
        LOG.debug(sorted_projects)

        # Create table
        table = Table(
            title="Data Delivery System usage",
            caption=(
                "The cost is calculated from the pricing provided by Safespring "
                "(unit kr/GB/month) and is therefore approximate. Contact the Data Centre for more details."
            ),
            show_header=True,
            header_style="bold",
            show_footer=True,
        )

        # Add columns
        table.add_column("Project ID", footer="Total")
        table.add_column("GBHours", footer=str(total_usage["gbhours"]))
        table.add_column(
            "Approx. Cost (kr)",
            footer=str(total_usage["cost"]) if total_usage["cost"] > 1 else str(0),
        )

        # Add rows
        for proj in sorted_projects:
            table.add_row(
                *[
                    proj,
                    str(project_usage[proj]["gbhours"]),
                    str(project_usage[proj]["cost"]) if project_usage[proj]["cost"] > 1 else str(0),
                ],
            )

        # Print out table
        console = Console()
        console.print(table)

    def list_projects(self, prompt_project=False, sort_by="Updated"):
        """Gets a list of all projects the user is involved in."""

        # Get projects from API
        try:
            response = requests.get(
                DDSEndpoint.LIST_PROJ, headers=self.token, params={"usage": self.show_usage}
            )
        except requests.exceptions.RequestException as err:
            raise exceptions.APIError(f"Problem with database response: {err}")

        if not response.ok:
            raise exceptions.APIError(f"Failed to get list of projects: {response.text}")

        try:
            resp_json = response.json()
        except simplejson.JSONDecodeError as err:
            raise exceptions.APIError(f"Could not decode JSON response: {err}")

        # Cancel if user not involved in any projects
        usage_info = resp_json.get("total_usage")
        project_info = resp_json.get("project_info")
        if not project_info:
            raise exceptions.NoDataError("No project info was retrieved. No files to list.")

        # Sort projects according to chosen or default
        sorted_projects = list()
        # TODO (ina): Put this in another class or function?
        sorting_dict = {
            "title": "Title",
            "pi": "PI",
            "status": "Status",
            "updated": "Last updated",
            "size": "Size",
            "usage": "GBHours",
            "cost": "Cost",
        }
        sort_by = sort_by.lower()
        if sort_by in ["usage", "cost"] and not self.show_usage:
            LOG.warning(f"Can only sort by {sort_by} when using the --usage flag.")
            sort_by = "updated"

        sorted_projects = sorted(project_info, key=lambda i: i["Project ID"])

        if sort_by != "id":
            sort_by = sorting_dict[sort_by]
            sorted_projects = sorted(
                sorted_projects,
                key=lambda t: (t[sort_by] is None, t[sort_by]),
                reverse=sort_by == "updated",
            )

        # Column format
        # TODO (ina): Put this in another class or function?
        default_format = {"justify": "left", "style": "", "footer": "", "overflow": "fold"}
        columns = {
            "Project ID": {
                "justify": default_format.get("justify"),
                "style": "green",
                "footer": "Total" if self.show_usage else "",
                "overflow": default_format.get("overflow"),
            },
            **{x: default_format for x in ["Title", "PI", "Status", "Last updated"]},
            "Size": {
                "justify": "center",
                "style": default_format.get("style"),
                "footer": resp_json.get("total_size"),
                "overflow": "ellipsis",
            },
        }

        if usage_info and self.show_usage:
            columns.update(
                {
                    "GBHours": {
                        "justify": "center",
                        "style": default_format.get("style"),
                        "footer": str(usage_info["gbhours"]),
                        "overflow": "ellipsis",
                    },
                    "Cost": {
                        "justify": "center",
                        "style": default_format.get("style"),
                        "footer": str(usage_info["cost"]),
                        "overflow": "ellipsis",
                    },
                }
            )

        # Create table
        table = Table(
            title="Your Projects",
            show_header=True,
            header_style="bold",
            show_footer=self.show_usage,
            caption=(
                "The cost is calculated from the pricing provided by Safespring (unit kr/GB/month) "
                "and is therefore approximate. Contact the Data Centre for more details."
            )
            if self.show_usage
            else None,
        )

        # Add columns to table
        for colname, colformat in columns.items():
            table.add_column(
                colname,
                justify=colformat["justify"],
                style=colformat["style"],
                footer=colformat["footer"],
                overflow=colformat["overflow"],
            )

        # Add all column values for each row to table
        for proj in sorted_projects:
            table.add_row(*[proj[i] for i in columns])

        # Print to stdout if there are any lines
        console = Console()
        if table.columns:
            # Use a pager if output is taller than the visible terminal
            if len(sorted_projects) + 5 > console.height:
                with console.pager():
                    console.print(table)
            else:
                console.print(table)
        else:
            raise exceptions.NoDataError(f"No projects found")

        # Return the list of projects
        return sorted_projects

    def list_files(self, folder: str = None, show_size: bool = False):
        """Create a tree displaying the files within the project."""

        LOG.info(f"Listing files for project '{self.project}'")
        if folder:
            LOG.info(f"Showing files in folder '{folder}'")

        # Make call to API
        try:
            response = requests.get(
                DDSEndpoint.LIST_FILES,
                params={"subpath": folder, "show_size": show_size},
                headers=self.token,
            )
        except requests.exceptions.RequestException as err:
            raise exceptions.APIError(f"Problem with database response: '{err}'")

        if not response.ok:
            raise exceptions.APIError(f"Failed to get list of files: '{response.text}'")

        # Get response
        try:
            resp_json = response.json()
        except simplejson.JSONDecodeError as err:
            raise exceptions.APIError(f"Could not decode JSON response: '{err}'")

        # Check if project empty
        if "num_items" in resp_json and resp_json["num_items"] == 0:
            raise exceptions.NoDataError(f"Project '{self.project}' is empty.")

        # Get files
        files_folders = resp_json["files_folders"]

        # Sort the file/folders according to names
        sorted_files_folders = sorted(files_folders, key=lambda f: f["name"])

        # Create tree
        tree_title = folder if folder else f"Files / directories in project: [green]{self.project}"
        tree = Tree(f"[bold magenta]{tree_title}")

        if not sorted_files_folders:
            raise exceptions.NoDataError(f"Could not find folder: '{folder}'")

        # Get max length of file name
        max_string = max([len(x["name"]) for x in sorted_files_folders])

        # Get max length of size string
        sizes = [len(x["size"][0]) for x in sorted_files_folders if show_size and "size" in x]
        max_size = max(sizes) if sizes else 0

        # Visible folders
        visible_folders = []

        # Add items to tree
        for x in sorted_files_folders:
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
                visible_folders.append(x["name"])
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

        # Print output to stdout
        console = Console()
        if len(files_folders) + 5 > console.height:
            with console.pager():
                console.print(Padding(tree, 1))
        else:
            console.print(Padding(tree, 1))

        # Return variable
        return visible_folders
