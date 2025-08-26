"""Data Delivery System Project info manager."""

# Standard library
import logging
import sys

# Installed
import rich


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
            token_path=token_path,
        )
        self.project = project

    # Public methods ###################### Public methods #

    def show_project_info(self):
        """Display info about a project."""

        # Get project info from api
        project_info = self.get_project_info()
        table = self.generate_project_table(project_info=project_info)
        dds_cli.utils.console.print(table)

        # Print Title and Description below the table
        dds_cli.utils.console.print(f"[b]Project title:[/b]       {project_info['Title']}")
        dds_cli.utils.console.print(f"[b]Project description:[/b] {project_info['Description']}")

    def update_info(self, title=None, description=None, pi=None):  # pylint: disable=invalid-name
        """Update project info"""

        if all(item is None for item in [title, description, pi]):
            raise exceptions.NoDataError(
                "Please specify which information you would like to change: '--title', "
                "'--description' or/and '--principal-investigator'."
            )

        # Get project info from API
        project_info = self.get_project_info()

        # Collect the items for change and ask for confirmation for each of them
        info_items = {}
        if title:
            info_items["title"] = title
            # Ask the user for confirmation
            if not rich.prompt.Confirm.ask(
                f"You are about to change the [i]title[/i] for project '[b]{self.project}[/b]'\n"
                f"[b][blue]from[/blue][/b]\t{project_info['Title']}\n"
                f"[b][green]to[/green][/b]\t{info_items['title']}\n"
                "Are you sure?"
            ):
                LOG.info("Probably for the best. Exiting.")
                sys.exit(0)
        if description:
            info_items["description"] = description
            # Ask the user for confirmation
            if not rich.prompt.Confirm.ask(
                f"You are about to change the [i]description[/i] for project '[b]{self.project}[/b]' \n"
                f"[b][blue]from[/blue][/b]\t{project_info['Description']}\n"
                f"[b][green]to[/green][/b]\t{info_items['description']} \n"
                "Are you sure?"
            ):
                LOG.info("Probably for the best. Exiting.")
                sys.exit(0)
        if pi:
            info_items["pi"] = pi
            # Ask the user for confirmation
            if not rich.prompt.Confirm.ask(
                f"You are about to change the [i]PI[/i] for project '[b]{self.project}[/b]' \n"
                f"[b][blue]from[/blue][/b]\t{project_info['PI']}\n"
                f"[b][green]to[/green][/b]\t{info_items['pi']} \n"
                "Are you sure?"
            ):
                LOG.info("Probably for the best. Exiting.")
                sys.exit(0)

        # Run the request
        response_json, _ = dds_cli.utils.perform_request(
            endpoint=DDSEndpoint.PROJ_INFO,
            headers=self.token,
            method="put",
            params={"project": self.project},
            json=info_items,
            error_message="Failed to update project info",
        )

        # Print the information items after the change
        dds_cli.utils.console.print(f"Project {response_json.get('message')}")
        dds_cli.utils.console.print(f"[b]Project title:[/b]         {response_json.get('title')}")
        dds_cli.utils.console.print(
            f"[b]Project description:[/b]   {response_json.get('description')}"
        )
        dds_cli.utils.console.print(f"[b]Project PI:[/b]            {response_json.get('pi')}")
