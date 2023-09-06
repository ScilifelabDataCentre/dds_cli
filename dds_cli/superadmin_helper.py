"""Maintenance Manager module."""

####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
###################################################################################################

# Standard library
import logging

# Installed

# Own modules
import dds_cli
import dds_cli.auth
import dds_cli.base
import dds_cli.exceptions
import dds_cli.utils

# from dds_cli import exceptions
from dds_cli import DDSEndpoint


####################################################################################################
# START LOGGING CONFIG ###################################################### START LOGGING CONFIG #
####################################################################################################

LOG = logging.getLogger(__name__)


####################################################################################################
# CLASSES ################################################################################ CLASSES #
####################################################################################################


class SuperAdminHelper(dds_cli.base.DDSBaseClass):
    """Admin class."""

    def __init__(
        self,
        authenticate: bool = True,
        no_prompt: bool = False,
        token_path: str = None,
    ):
        """Initialize, incl. user authentication."""
        # Initiate DDSBaseClass to authenticate user
        super().__init__(
            authenticate=authenticate,
            method=False,
            no_prompt=no_prompt,
            token_path=token_path,
        )

    def change_maintenance_mode(self, setting) -> None:
        """Change Maintenance mode."""
        response_json, _ = dds_cli.utils.perform_request(
            endpoint=DDSEndpoint.MAINTENANCE,
            headers=self.token,
            method="put",
            json={"state": setting},
            error_message="Failed setting maintenance mode",
        )

        response_message = response_json.get(
            "message", "No response. Cannot confirm setting maintenance mode."
        )
        LOG.info(response_message)

    def display_maintenance_mode_status(self) -> None:
        """Display Maintenance mode status."""
        response_json, _ = dds_cli.utils.perform_request(
            endpoint=DDSEndpoint.MAINTENANCE,
            headers=self.token,
            method="get",
            error_message="Failed getting maintenance mode status",
        )

        response_message = response_json.get(
            "message", "No response. Cannot display maintenance mode status."
        )
        LOG.info(response_message)
        
    def get_stats(self) -> None:
        """Get rows from statistics."""
        response_json, _ = dds_cli.utils.perform_request(
            endpoint=DDSEndpoint.STATS,
            headers=self.token,
            method="get",
            error_message="Failed getting statistics from API.",
        )
        LOG.debug(response_json)

        # Get items from response
        stats = response_json.get("stats")
        if not stats:
            raise dds_cli.exceptions.ApiResponseError(message="No stats were returned from API.")

        # Format table consisting of user stats
        table_users = dds_cli.utils.create_table(
            title="Units and accounts",
            columns=[
                "Date",
                "Units",
                "Researchers",
                "Project Owners",
                "Unit Personnel",
                "Unit Admins",
                "Super Admins",
                "Total Users",
            ],
            rows=stats,
            caption=(
                "Number of Units using the DDS for data deliveries, and number of accounts with different roles.\n"
                # "[underline]Researchers[/underline]:  "
                # "[underline]Project Owners[/underline]: 
                # "[underline]Unit Personnel[/underline]:  "
                # "[underline]Unit Admins[/underline]:  "
                # "[underline]Super Admins[/underline]: 
                # "[underline]Total Users[/underline]: 
            ),
        )
        dds_cli.utils.console.print(
            table_users, "\n"
        )  # TODO: Possibly change to print_or_page later on, or give option to save stats

        # Format table consisting of project and data stats
        table_data = dds_cli.utils.create_table(
            title="Amount of data delivered via the DDS",
            columns=[
                "Date",
                "Active Projects",
                "Inactive Projects",
                "Total Projects",
                "Data Now (TB)",
                "Data Uploaded (TB)",
                "TBHours Last Month",
                "TBHours Total",
            ],
            rows=stats,
            caption=(
                "Number of delivery projects and amount of data that is being (and has been) delivered via the DDS.\n"
                # "[underline]Date[/underline]: "
                # "[underline]Active Projects[/underline]: "
                # "[underline]Inactive Projects[/underline]: "
                # "[underline]Total Projects[/underline]:  "
                # "[underline]Data Now (TB)[/underline]: "
                # "[underline]Data Uploaded (TB)[/underline]: "
                # "[underline]TBHours Last Month[/underline]: "
                # "[underline]TBHours Total[/underline]: "
            ),
        )
        dds_cli.utils.console.print(
            table_data, "\n"
        )  # TODO: Possibly change to print_or_page later on, or give option to save stats
