"""Data Delivery System Project info manager."""
import logging

# Installed
import requests
import simplejson
import pytz
import tzlocal
import datetime

# Own modules
from dds_cli import base
from dds_cli import exceptions
from dds_cli import DDSEndpoint
import dds_cli.utils

###############################################################################
# START LOGGING CONFIG ################################# START LOGGING CONFIG #
###############################################################################

LOG = logging.getLogger(__name__)


###############################################################################
# CLASSES ########################################################### CLASSES #
###############################################################################


class ProjectInfoManager(base.DDSBaseClass):
    """Project info manager class."""

    def __init__(
        self,
        project: str,
        no_prompt: bool = False,
        token_path: str = None,
    ):
        """Handle actions regarding project info in the cli."""
        # Initiate DDSBaseClass to authenticate user
        super().__init__(
            no_prompt=no_prompt,
            method_check=False,
            token_path=token_path,
        )
        self.project = project

    # Public methods ###################### Public methods #
    def show_project_info(self):
        """Get a project info."""
        # Get info about a project from API
        response, _ = dds_cli.utils.perform_request(
            DDSEndpoint.PROJ_INFO,
            method="get",
            headers=self.token,
            params={"project": self.project},
            error_message="Failed to get project information",
        )

        project_info = response.get("project_info")

        # Print project info table
        table = dds_cli.utils.create_table(
            title="Project information.",
            columns=["Project ID", "Created by", "Status", "Last updated", "Size"],
            rows=[
                project_info,
            ],
            caption=f"Information about project {project_info['Project ID']}",
        )
        dds_cli.utils.console.print(table)

        # Print Title and Description below the table
        dds_cli.utils.console.print(f"[b]Project title:[/b]       {project_info['Title']}")
        dds_cli.utils.console.print(f"[b]Project description:[/b] {project_info['Description']}")

    def update_info(self, title=None, description=None, pi=None):
        """Update project info"""

        info_items = {}
        if title:
            info_items["title"] = title
        if description:
            info_items["description"] = description
        if pi:
            info_items["pi"] = pi

        response_json, _ = dds_cli.utils.perform_request(
            endpoint=DDSEndpoint.PROJ_INFO,
            headers=self.token,
            method="put",
            params={"project": self.project},
            json=info_items,
            error_message="Failed to update project info",
        )

        dds_cli.utils.console.print(f"Project {response_json.get('message')}")
        dds_cli.utils.console.print(f"[b]Project title:[/b]       {response_json.get('title')}")
        dds_cli.utils.console.print(
            f"[b]Project description:[/b] {response_json.get('description')}"
        )
        dds_cli.utils.console.print(f"[b]Project PI:[/b] {response_json.get('pi')}")
