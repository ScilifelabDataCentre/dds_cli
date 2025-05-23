"""Data Lister -- Lists the projects and project content."""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
from dataclasses import dataclass
import logging
from typing import Tuple, Union, List
import datetime
import pathlib

# Installed
from rich.padding import Padding
from rich.markup import escape
from rich.table import Table
from rich.tree import Tree
import pytz
import tzlocal

# Own modules
from dds_cli import base
from dds_cli import exceptions
import dds_cli.utils
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
        method: str = "ls",
        project: str = None,
        show_usage: bool = False,
        tree: bool = False,
        no_prompt: bool = False,
        json: bool = False,
        token_path: str = None,
        binary: bool = False,
    ):
        """Handle actions regarding data listing in the cli."""
        # Only method "ls" can use the DataLister class
        if method != "ls":
            raise exceptions.InvalidMethodError(
                attempted_method=method, message="DataLister attempting unauthorized method"
            )

        # Initiate DDSBaseClass to authenticate user
        super().__init__(
            project=project,
            method=method,
            no_prompt=no_prompt,
            token_path=token_path,
        )

        self.show_usage = show_usage
        self.tree = tree
        self.json = json
        self.binary = binary

    # Public methods ########################### Public methods #

    def list_projects(self, sort_by="Updated", show_all: bool = False):
        """Get a list of project(s) the user is involved in."""
        # Get projects from API
        response, _ = dds_cli.utils.perform_request(
            DDSEndpoint.LIST_PROJ,
            headers=self.token,
            method="get",
            json={"usage": self.show_usage, "show_all": show_all},
            error_message="Failed to get list of projects",
            timeout=DDSEndpoint.TIMEOUT,
        )

        # Cancel if user not involved in any projects
        usage_info = response.get("total_usage")
        total_size = response.get("total_size")
        project_info = response.get("project_info")
        always_show = response.get("always_show", False)
        if not project_info:
            raise exceptions.NoDataError("No project info was retrieved. No files to list.")
        for project in project_info:
            try:
                last_updated = pytz.timezone("UTC").localize(
                    datetime.datetime.strptime(project["Last updated"], "%a, %d %b %Y %H:%M:%S GMT")
                )
            except ValueError as exc:
                raise exceptions.ApiResponseError(
                    f"Time zone mismatch: Incorrect zone '{project['Last updated'].split()[-1]}'"
                ) from exc

            project["Last updated"] = last_updated.astimezone(tzlocal.get_localzone()).strftime(
                "%a, %d %b %Y %H:%M:%S %Z"
            )

        # Sort projects according to chosen or default, first ID
        sorted_projects = self.__sort_projects(projects=project_info, sort_by=sort_by)

        if not self.json:
            self.__print_project_table(sorted_projects, usage_info, total_size, always_show)

        # Return the list of projects
        return sorted_projects

    def list_files(self, folder: str = None, show_size: bool = False):
        """Create a tree displaying the files within the project."""
        LOG.info("Listing files for project '%s'", self.project)
        if folder:
            LOG.info("Showing files in folder '%s'", escape(str(folder)))

        if folder is None:
            folder = ""
        # Make call to API
        response, _ = dds_cli.utils.perform_request(
            DDSEndpoint.LIST_FILES,
            method="get",
            params={"project": self.project},
            json={"subpath": folder, "show_size": show_size},
            headers=self.token,
            error_message="Failed to get list of files in project",
            timeout=DDSEndpoint.TIMEOUT,
        )

        # Check if project empty
        if "num_items" in response and response["num_items"] == 0:
            raise exceptions.NoDataError(f"Project '{self.project}' is empty.")

        # Get files
        files_folders = response["files_folders"]

        # Sort the file/folders according to names
        sorted_files_folders = sorted(files_folders, key=lambda f: f["name"])

        # Create tree
        tree_title = escape(str(folder)) or f"Files / directories in project: [green]{self.project}"
        tree = Tree(f"[bold magenta]{tree_title}")

        if not sorted_files_folders:
            raise exceptions.NoDataError(f"Could not find folder: '{escape(folder)}'")

        # Get max length of file name
        max_string = max(len(x["name"]) for x in sorted_files_folders)

        # Get max length of size string
        max_size = max(
            (
                len(
                    dds_cli.utils.format_api_response(
                        response=x["size"], key="Size", binary=self.binary
                    ).split(" ", maxsplit=1)[0]
                )
                for x in sorted_files_folders
                if show_size and "size" in x
            ),
            default=0,
        )

        # Visible folders
        visible_folders = []

        # Add items to tree
        for item in sorted_files_folders:
            # Check if string is folder
            is_folder = item.pop("folder")

            # Att 1 for folders due to trailing /
            tab = th.TextHandler.format_tabs(
                string_len=len(item["name"]) + (1 if is_folder else 0),
                max_string_len=max_string,
            )

            # Add formatting if folder and set string name
            line = ""
            if is_folder:
                line = "[bold deep_sky_blue3]"
                visible_folders.append(item["name"])
            line += escape(item["name"]) + ("/" if is_folder else "")

            # Add size to line if option specified
            if show_size and "size" in item:
                size = dds_cli.utils.format_api_response(
                    response=item["size"], key="Size", binary=self.binary
                )
                line += f"{tab}{size.split()[0]}"

                # Define space between number and size format
                tabs_bf_format = th.TextHandler.format_tabs(
                    string_len=len(size), max_string_len=max_size, tab_len=2
                )
                line += f"{tabs_bf_format}{size.split()[1]}"
            tree.add(line)

        # Print output to stdout
        if len(files_folders) + 5 > dds_cli.utils.console.height:
            with dds_cli.utils.console.pager():
                dds_cli.utils.console.print(Padding(tree, 1))
        else:
            dds_cli.utils.console.print(Padding(tree, 1))

        # Return variable
        return visible_folders

    def list_recursive(self, show_size: bool = False):
        """Recursively list project contents."""

        @dataclass
        class FileTree:
            """Container class for holding information about the remote file tree."""

            subtrees: List[Union["FileTree", Tuple[str, str]]] = None
            name: str = None

        def __api_call_list_files(folder: str):
            # Make call to API
            resp_json, _ = dds_cli.utils.perform_request(
                DDSEndpoint.LIST_FILES,
                method="get",
                params={"project": self.project},
                json={"subpath": folder, "show_size": show_size},
                headers=self.token,
                error_message="Failed to list the project's directory tree",
            )

            if not "files_folders" in resp_json:
                raise exceptions.NoDataError(f"Could not find folder: '{folder}'")

            sorted_files_folders = sorted(resp_json["files_folders"], key=lambda f: f["name"])

            if not sorted_files_folders:
                raise exceptions.NoDataError(f"Could not find folder: '{folder}'")

            return sorted_files_folders

        def __construct_file_tree(folder: str, basename: str) -> Tuple[FileTree, int, int]:
            """
            Recurses through the project directories.

            Constructs a file tree by subsequent calls to the API
            """
            tree = FileTree([], f"{basename}/")
            try:
                sorted_files_folders = __api_call_list_files(folder)
            except exceptions.NoDataError as exc:
                if folder is None:
                    raise exceptions.NoDataError(
                        "No files or folders found for the specified project"
                    ) from exc

                raise exceptions.NoDataError(f"Could not find folder: '{escape(folder)}'") from exc

            # Get max length of file name
            max_string = max(len(x["name"]) for x in sorted_files_folders)

            # Get max length of size string
            max_size = max(
                (
                    len(x["size"].split(" ")[0])
                    for x in sorted_files_folders
                    if show_size and "size" in x
                ),
                default=0,
            )

            # Rich outputs precisely one line per file/folder
            for item in sorted_files_folders:
                is_folder = item.pop("folder")

                if not is_folder:
                    tree.subtrees.append(
                        (escape(item["name"]), item.get("size") if show_size else None)
                    )
                else:
                    subtree, _max_string, _max_size = __construct_file_tree(
                        pathlib.Path(folder, item["name"]).as_posix() if folder else item["name"],
                        f"[bold deep_sky_blue3]{escape(item['name'])}",
                    )
                    # Due to indentation, the filename strings of
                    # subdirectories are 4 characters deeper than
                    # their parent directories
                    max_string = max(max_string, _max_string + 4)
                    max_size = max(max_size, _max_size)
                    tree.subtrees.append(subtree)

            return tree, max_string, max_size

        def __construct_file_dict_tree(folder: str) -> dict:
            """
            Recurses through the project directories.

            Constructs a file tree by subsequent calls to the API
            """
            try:
                sorted_files_folders = __api_call_list_files(folder)
            except exceptions.NoDataError as exc:
                if folder is None:
                    raise exceptions.NoDataError(
                        "No files or folders found for the specified project"
                    ) from exc

                raise exceptions.NoDataError(f"Could not find folder: '{folder}'") from exc

            tree = {}

            for item in sorted_files_folders:
                is_folder = item.pop("folder")
                name = item["name"]
                if not is_folder:
                    tree[name] = {"name": name, "is_folder": False, "children": {}}
                    if show_size:
                        tree[item["name"]]["size"] = item.get("size")
                else:
                    children = __construct_file_dict_tree(
                        pathlib.Path(folder, name).as_posix() if folder else name,
                    )
                    tree[name] = {"name": name, "is_folder": True, "children": children}

            return tree

        def __construct_rich_tree(
            file_tree: FileTree, max_str: int, max_size: int, depth: int
        ) -> Tuple[Tree, int]:
            """Construct the rich tree from the file tree."""
            tree = Tree(file_tree.name)
            tree_length = len(file_tree.subtrees)
            for node in file_tree.subtrees:
                if isinstance(node, FileTree):
                    subtree, length = __construct_rich_tree(node, max_str, max_size, depth + 1)
                    tree.add(subtree)
                    tree_length += length
                else:
                    line = node[0]
                    if show_size and node[1] is not None:
                        tab = th.TextHandler.format_tabs(
                            string_len=len(node[0]),
                            max_string_len=max_str - 4 * depth,
                        )
                        line += f"{tab}{node[1].split()[0]}"

                        # Define space between number and size format
                        tabs_bf_format = th.TextHandler.format_tabs(
                            string_len=len(node[1].split()[1]),
                            max_string_len=max_size,
                            tab_len=2,
                        )
                        line += f"{tabs_bf_format}{node[1].split()[1]}"
                    tree.add(line)

            return tree, tree_length

        if self.json:
            tree_dict = __construct_file_dict_tree(None)
            return tree_dict

        # We use two tree walks, one for file search and one for Rich tree
        # constructing, since it is difficult to compute the correct size
        # indentation without the whole tree
        file_tree, max_string, max_size = __construct_file_tree(
            None, f"[bold magenta]Files & directories in project: [green]{self.project}"
        )

        tree, tree_length = __construct_rich_tree(file_tree, max_string, max_size, 0)

        # The first header is not accounted for by the recursion
        tree_length += 1

        # Check if the tree is too large to be printed directly
        # and use a pager if that is the case
        if tree_length > dds_cli.utils.console.height:
            with dds_cli.utils.console.pager():
                dds_cli.utils.console.print(
                    Padding(
                        tree,
                        1,
                    )
                )
        else:
            dds_cli.utils.console.print(
                Padding(
                    tree,
                    1,
                )
            )

        return None

    def list_users(self):
        """Get a list of user(s) involved in a project."""
        # Get user list from API
        resp_json, _ = dds_cli.utils.perform_request(
            DDSEndpoint.LIST_PROJ_USERS,
            method="get",
            headers=self.token,
            params={"project": self.project},
            error_message="Failed to get list of users",
        )

        research_users = resp_json.get("research_users")

        # Print users
        if not self.json:
            self.__print_users_table(research_users)

        return research_users

    # Private methods ###################################################### Private methods #

    # Project listing
    def __sort_projects(self, projects, sort_by="id"):
        """Sort the projects according to ID and either default or chosen column."""
        # Lower case sort_by options and their column title equivalents
        sorting_dict = {
            "id": "Project ID",
            "title": "Title",
            "pi": "PI",
            "status": "Status",
            "updated": "Last updated",
            "size": "Size",
            "usage": "Usage",
            "cost": "Cost",
        }

        # Get lower case option
        sort_by = sort_by.lower()

        # Check if sorting column allowed
        if sort_by in ["usage", "cost"] and not self.show_usage:
            LOG.warning("Can only sort by %s when using the --usage flag.", sort_by)
            sort_by = "updated"

        # Sort according to ID
        sorted_projects = sorted(projects, key=lambda i: i["Project ID"])

        # Sort again according to chosen of default option
        sort_by = sorting_dict.get(sort_by)
        if sort_by:
            sorted_projects = sorted(
                sorted_projects,
                key=lambda t: (t[sort_by] is None, t[sort_by]),
                reverse=sort_by == sorting_dict.get("updated"),
            )

        return sorted_projects

    def __format_project_columns(self, total_size=None, usage_info=None):
        """Define the formatting for the project table according to what is returned from API."""
        default_format = {"justify": "left", "style": "", "footer": "", "overflow": "fold"}

        # Choose formattting
        column_formatting = {
            "Project ID": {
                "justify": default_format.get("justify"),
                "style": "green",
                "footer": "Total" if self.show_usage else default_format.get("footer"),
                "overflow": default_format.get("overflow"),
            },
            **{x: default_format for x in ["Title", "PI", "Created by", "Status", "Last updated"]},
        }

        if total_size is not None:
            column_formatting["Size"] = {
                "justify": "right",
                "style": default_format.get("style"),
                "footer": dds_cli.utils.format_api_response(total_size, key="Size"),
                "overflow": "ellipsis",
            }

        if usage_info and self.show_usage:
            # Only display costs above 1 kr
            column_formatting.update(
                {
                    "Usage": {
                        "justify": "right",
                        "style": default_format.get("style"),
                        "footer": dds_cli.utils.format_api_response(
                            usage_info["usage"], key="Usage"
                        ),
                        "overflow": "ellipsis",
                    },
                    "Cost": {
                        "justify": "right",
                        "style": default_format.get("style"),
                        "footer": dds_cli.utils.format_api_response(usage_info["cost"], key="Cost"),
                        "overflow": "ellipsis",
                    },
                }
            )

        column_formatting["Access"] = {
            "justify": "left",
            "style": default_format.get("style"),
            "footer": default_format.get("footer"),
            "overflow": default_format.get("overflow"),
        }

        return column_formatting

    def __print_project_table(self, sorted_projects, usage_info, total_size, always_show):
        # Column format
        column_formatting = self.__format_project_columns(
            total_size=total_size, usage_info=usage_info
        )

        # Create table
        table = Table(
            title="Your Project(s)",
            show_header=True,
            header_style="bold",
            show_footer=self.show_usage and "Usage" in column_formatting,
            caption=(
                (
                    "The cost is calculated from the pricing provided by Safespring (unit kr/GB/month) "
                    "and is therefore approximate. Contact the Data Centre for more details."
                )
                if self.show_usage
                else None
            ),
        )

        # Add columns to table
        for colname, colformat in column_formatting.items():
            table.add_column(
                colname,
                justify=colformat["justify"],
                style=colformat["style"],
                footer=colformat["footer"],
                overflow=colformat["overflow"],
            )

        # Add all column values for each row to table
        for proj in sorted_projects:
            new_row = []
            for column in column_formatting:
                if column == "Size" and proj["Status"] != "Available" and not always_show:
                    new_row.append("---")
                else:
                    new_row.append(
                        escape(
                            dds_cli.utils.format_api_response(
                                response=proj[column], key=column, binary=self.binary
                            )
                        )
                    )
            table.add_row(*new_row)

        # Print to stdout if there are any lines
        dds_cli.utils.print_or_page(item=table)

    # User listing
    def __print_users_table(self, research_users):
        # TODO: call on future list_project_users function, will be implemented for dds user ls --project
        default_format = {"justify": "left", "style": "", "footer": "", "overflow": "fold"}
        column_formatting = {
            **{x: default_format for x in ["User Name", "Primary email", "Role"]},
        }
        table = Table(
            title="Project User(s)",
            show_header=True,
            header_style="bold",
        )
        # Add columns to table
        for colname, colformat in column_formatting.items():
            table.add_column(
                colname,
                justify=colformat["justify"],
                style=colformat["style"],
                footer=colformat["footer"],
                overflow=colformat["overflow"],
            )

        # Add all column values for each row to table
        for user in research_users:
            table.add_row(*[user[i] for i in column_formatting])

        # Print to stdout if there are any lines
        if table.rows:
            # Use a pager if output is taller than the visible terminal
            if len(research_users) + 5 > dds_cli.utils.console.height:
                with dds_cli.utils.console.pager():
                    dds_cli.utils.console.print(table)
            else:
                dds_cli.utils.console.print(table)
        else:
            raise exceptions.NoDataError("No users found.")
