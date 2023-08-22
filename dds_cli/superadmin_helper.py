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
        method: str = "off",
        no_prompt: bool = False,
        token_path: str = None,
    ):
        """Initialize, incl. user authentication."""
        # Initiate DDSBaseClass to authenticate user
        super().__init__(
            authenticate=authenticate,
            method=method,
            no_prompt=no_prompt,
            token_path=token_path,
        )

        # Only methods "on" and "off" can use the Maintenance class
        if self.method not in ["on", "off"]:
            raise dds_cli.exceptions.InvalidMethodError(f"Unauthorized method: '{self.method}'")

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
                "[underline]Date[/underline]: Date on which the stats were recorded in the database. "
                "[underline]Researchers[/underline]: Number of accounts with the role 'Researcher'. "
                "[underline]Project Owners[/underline]: Number of (unique) 'Researcher' accounts with admin "
                "permissions in at least one project. "
                "[underline]Unit Personnel[/underline]: Number of accounts with the role 'Unit Personnel'. "
                "[underline]Unit Admins[/underline]: Number of accounts with the role 'Unit Admin'. "
                "[underline]Super Admins[/underline]: Number of employees at the SciLifeLab Data Centre with the "
                "DDS account role 'Super Admin'. "
                "[underline]Total Users[/underline]: Total number of accounts. Project Owners are a subrole of "
                "'Researchers' and are therefore not included in the summary."
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
                "[underline]Date[/underline]: Date on which the stats were recorded in the database. "
                "[underline]Active Projects[/underline]: Delivery projects currently used to deliver data. Statuses "
                "included are 'In Progress', 'Available' and 'Expired'. "
                "[underline]Inactive Projects[/underline]: Delivery projects that have previously been created and/or "
                "used for data deliveries. Statuses included are 'Deleted', 'Archived' (incl. aborted). "
                "[underline]Total Projects[/underline]: Sum of active- and inactive projects. "
                "[underline]Data Now (TB)[/underline]: Number of terrabytes of data that are currently being delivered "
                "with the DDS. "
                "[underline]Data Uploaded (TB)[/underline]: Total number of terrabytes of data that have been uploaded "
                "to the DDS temporary storage location since the DDS went into production. "
                "[underline]TBHours Last Month[/underline]: Number of terrabyte hours that were recorded in the DDS "
                "the previous month. "
                "[underline]TBHours Total[/underline]: Total number of terrabyte hours that have been recorded in the "
                "DDS since going into production."
            ),
        )
        dds_cli.utils.console.print(
            table_data, "\n"
        )  # TODO: Possibly change to print_or_page later on, or give option to save stats
