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
        # Get stats from API
        response_json, _ = dds_cli.utils.perform_request(
            endpoint=DDSEndpoint.STATS,
            headers=self.token,
            method="get",
            error_message="Failed getting statistics from API.",
        )

        # Get items from response
        stats, columns = dds_cli.utils.get_required_in_response(
            keys=["stats", "columns"], response=response_json
        )

        # Format table consisting of user stats
        user_stat_columns = [
            "Date",
            "Units",
            "Researchers",
            "Project Owners",
            "Unit Personnel",
            "Unit Admins",
            "Super Admins",
            "Total Users",
        ]
        column_descriptions = " ".join(
            f"[underline]{col}[/underline]: {columns[col]}" for col in user_stat_columns
        )
        table_users = dds_cli.utils.create_table(
            title="Units and accounts",
            columns=user_stat_columns,
            rows=stats,
            caption=(
                "Number of Units using the DDS for data deliveries, "
                f"and number of accounts with different roles.\n {column_descriptions}"
            ),
        )
        dds_cli.utils.console.print(
            table_users, "\n"
        )  # TODO: Possibly change to print_or_page later on, or give option to save stats

        # Format table consisting of project and data stats
        project_stat_columns = [
            "Date",
            "Active Projects",
            "Inactive Projects",
            "Total Projects",
            "Data Now (TB)",
            "Data Uploaded (TB)",
            "TBHours Last Month",
            "TBHours Total",
        ]
        column_descriptions = " ".join(
            f"[underline]{col}[/underline]: {columns[col]}" for col in project_stat_columns
        )
        table_data = dds_cli.utils.create_table(
            title="Amount of data delivered via the DDS",
            columns=project_stat_columns,
            rows=stats,
            caption=(
                "Number of delivery projects and amount of data that is being "
                f"(and has been) delivered via the DDS.\n {column_descriptions}"
            ),
        )
        dds_cli.utils.console.print(
            table_data, "\n"
        )  # TODO: Possibly change to print_or_page later on, or give option to save stats
