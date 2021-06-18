"""Usage Displayer -- Shows the usage per facility and project."""

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
from rich.table import Table

# Own modules
from dds_cli import base
from dds_cli import exceptions
from dds_cli import DDSEndpoint

###############################################################################
# START LOGGING CONFIG ################################# START LOGGING CONFIG #
###############################################################################

LOG = logging.getLogger(__name__)

###############################################################################
# CLASSES ########################################################### CLASSES #
###############################################################################


class UsageLister(base.DDSBaseClass):
    """Data lister class."""

    def __init__(
        self,
        username: str = None,
        config: pathlib.Path = None,
        project: str = None,
        project_level: bool = False,
    ):

        # Initiate DDSBaseClass to authenticate user
        super().__init__(username=username, config=config)

        # Only method "usage" can use the DataLister class
        if self.method != "usage":
            raise exceptions.AuthenticationError(f"Unauthorized method: '{self.method}'")

    def show_usage(self):
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
                "(unit kr/GB/month) and is therefore approximate."
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
