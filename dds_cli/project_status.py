"""Data Delivery System Project Status manager."""

import datetime
import logging
import typing
import sys
from dateutil.parser import parse

# Installed
import pytz
import tzlocal
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


class ProjectStatusManager(base.DDSBaseClass):
    """Project Status manager class."""

    def __init__(
        self,
        project: str,
        authenticate: bool = True,
        no_prompt: bool = False,
        token_path: str = None,
    ):
        """Handle actions regarding project status in the cli."""
        # Initiate DDSBaseClass to authenticate user
        super().__init__(
            authenticate=authenticate,
            no_prompt=no_prompt,
            token_path=token_path,
        )
        self.project = project

    # Public methods ###################### Public methods #

    def get_status(self, show_history):
        """Get current status and status history of the project."""
        resp_json, _ = dds_cli.utils.perform_request(
            DDSEndpoint.UPDATE_PROJ_STATUS,
            method="get",
            headers=self.token,
            params={"project": self.project},
            json={"history": show_history},
            error_message="Failed to get project status",
        )

        # Get result from API
        current_status = resp_json.get("current_status")
        current_deadline = resp_json.get("current_deadline")
        status_out = f"Current status of {self.project}: {current_status}"
        deadline_out = ""
        if current_deadline:
            try:
                date = pytz.timezone("UTC").localize(
                    datetime.datetime.strptime(current_deadline, "%a, %d %b %Y %H:%M:%S GMT")
                )
            except ValueError as exc:
                raise exceptions.ApiResponseError(
                    f"Time zone mismatch: Incorrect zone '{current_deadline.split()[-1]}'"
                ) from exc

            current_deadline = date.astimezone(tzlocal.get_localzone()).strftime(
                "%a, %d %b %Y %H:%M:%S %Z"
            )
            deadline_out = f" with deadline {current_deadline}"
        dds_cli.utils.console.print(f"{status_out}{deadline_out}")
        if show_history:
            history = "Status history \n"
            for row in resp_json.get("history"):
                try:
                    date = pytz.timezone("UTC").localize(
                        datetime.datetime.strptime(row[1], "%a, %d %b %Y %H:%M:%S GMT")
                    )
                except ValueError as exc:
                    raise exceptions.ApiResponseError(
                        f"Time zone mismatch: Incorrect zone '{row[1].split()[-1]}'"
                    ) from exc

                row[1] = date.astimezone(tzlocal.get_localzone()).strftime(
                    "%a, %d %b %Y %H:%M:%S %Z"
                )
                history += ", ".join(list(row)) + " \n"
            LOG.info(history)

    def update_status(self, new_status, deadline=None, is_aborted=False, no_mail=False):
        """Update project status"""

        extra_params = {"new_status": new_status, "send_email": not no_mail}
        if deadline:
            extra_params["deadline"] = deadline
        if is_aborted:
            extra_params["is_aborted"] = is_aborted

        # If the status is going to be archived or deleted. Ask for confirmation
        if new_status in ["Archived", "Deleted"]:
            # get project info
            try:
                project_info = self.get_project_info()
            except exceptions.ApiResponseError:
                dds_cli.utils.console.print(
                    "No project information could be displayed at this moment!"
                )
            else:
                table = self.generate_project_table(project_info=project_info)
                dds_cli.utils.console.print(table)

            # Create confirmation prompt
            print_info = (
                f"Are you sure you want to modify the status of {self.project}? All its contents "
            )
            if new_status == "Deleted":
                print_info += "and metainfo "
            print_info += (
                "will be deleted!\n"
                f"The project '{self.project}' is about to be [b][blue]{new_status}[/blue][/b].\n"
            )

            dds_cli.utils.console.print(print_info)

            if not rich.prompt.Confirm.ask("-"):
                LOG.info("Probably for the best. Exiting.")
                sys.exit(0)

        response_json, _ = dds_cli.utils.perform_request(
            endpoint=DDSEndpoint.UPDATE_PROJ_STATUS,
            headers=self.token,
            method="post",
            params={"project": self.project},
            json=extra_params,
            error_message="Failed to update project status",
        )

        dds_cli.utils.console.print(f"Project {response_json.get('message')}")

    def extend_deadline(self, new_deadline=None):
        """Extend the project deadline."""
        # Define initial parameters
        extra_params = {"send_email": False}

        # Fetch project status and default deadline
        response_json, _ = dds_cli.utils.perform_request(
            endpoint=DDSEndpoint.UPDATE_PROJ_STATUS,
            headers=self.token,
            method="patch",
            params={"project": self.project},
            json=extra_params,
            error_message="Failed to extend project deadline",
        )

        # Structure of the response:
        #   {
        #   'default_unit_days': 30,
        #   'project_info': {
        #       'Created by': 'First Unit User',
        #       'Description': 'This is a test project',
        #       'Last updated': 'Wed, 18 Oct 2023 08:40:43 GMT',
        #       'PI': 'support@example.com',
        #       'Project ID': 'project_1',
        #       'Size': 0,
        #       'Status': 'Available',
        #       'Title': 'First Project'
        #       },
        #   'project_status': {
        #       'current_deadline': 'Sat, 04 Nov 2023 23:59:59 GMT',
        #       'current_status': 'Available'},
        #   }

        # Check that the returned information was ok
        keys = ["project_info", "project_status", "default_unit_days"]
        (
            project_info,
            project_status,
            default_unit_days,
            *_,
        ) = dds_cli.utils.get_required_in_response(keys=keys, response=response_json)

        # Check and extract the required information for the operation
        current_status, *_ = dds_cli.utils.get_required_in_response(
            keys=["current_status"], response=project_status
        )

        # if the project is still in progress it won't have a current_deadline parameter
        if not current_status == "Available":
            raise exceptions.DDSCLIException(
                "You can only extend the deadline for a project that has the status 'Available'."
            )

        current_deadline, *_ = dds_cli.utils.get_required_in_response(
            keys=["current_deadline"], response=project_status
        )
        project_id, *_ = dds_cli.utils.get_required_in_response(
            keys=["Project ID"], response=project_info
        )

        # print information about the project status and table with the project info
        print_info = (
            f"\nCurrent deadline: [b][green]{current_deadline}[/green][/b]\n"
            f"Default deadline extension: [b][green]{default_unit_days}[/green][/b] days\n"
        )
        table = self.generate_project_table(project_info=project_info)
        dds_cli.utils.console.print(table)
        dds_cli.utils.console.print(print_info)

        # If it wasnt provided during the command click, ask the user for the new deadline
        if not new_deadline:
            # Question number of days to extend the deadline
            prompt_question = (
                "How many days would you like to extend the project deadline with? "
                "Leave empty in order to choose the default"
            )
            new_deadline = rich.prompt.IntPrompt.ask(prompt_question, default=default_unit_days)

        # Confirm operation question
        new_deadline_date = parse(current_deadline) + datetime.timedelta(days=new_deadline)
        new_deadline_date = new_deadline_date.strftime("%a,%d %b %Y %H:%M:%S")
        prompt_question = (
            f"\nThe new deadline for project {project_id} will be: [b][blue]{new_deadline_date}[/b][/blue]"
            "\n\n[b][blue]Are you sure [/b][/blue]you want to perform this operation? "
            "\nYou can only extend the data availability a maximum of "
            "[b][blue]3 times[/b][/blue], this consumes one of those times."
        )

        if not rich.prompt.Confirm.ask(prompt_question):
            LOG.info("Probably for the best. Exiting.")
            sys.exit(0)

        # Update parameters for the second request
        extra_params = {**extra_params, "confirmed": True, "new_deadline_in": new_deadline}

        response_json, _ = dds_cli.utils.perform_request(
            endpoint=DDSEndpoint.UPDATE_PROJ_STATUS,
            headers=self.token,
            method="patch",
            params={"project": self.project},
            json=extra_params,
            error_message="Failed to extend project deadline",
        )
        message = response_json.get("message")
        if not message:
            raise exceptions.DDSCLIException(
                "No message returned from API. Cannot verify extension of project deadline."
            )

        LOG.info(message)


class ProjectBusyStatusManager(base.DDSBaseClass):
    """Project Busy Status manager class."""

    def __init__(
        self,
        no_prompt: bool = False,
        token_path: str = None,
    ):
        """Handle actions regarding project busy status in the cli."""
        # Initiate DDSBaseClass to authenticate user
        super().__init__(
            no_prompt=no_prompt,
            token_path=token_path,
        )

    # Public methods ###################### Public methods #
    def get_busy_projects(self, show: bool = False):
        """Check if there are busy projects"""

        response_json, _ = dds_cli.utils.perform_request(
            endpoint=DDSEndpoint.PROJ_BUSY_ANY,
            method="get",
            headers=self.token,
            json={"list": show},
            error_message="Failed to get projects with busy status",
        )

        num_busy: int = response_json.get("num")
        if num_busy is None:
            raise exceptions.ApiResponseError("No info about busy projects returned from API.")

        if num_busy:
            if not show:
                LOG.info("There are %s busy projects at the moment.", num_busy)
            else:
                projects: typing.Dict = response_json.get("projects")
                LOG.info("The following projects are busy:")
                for proj in projects:
                    dds_cli.utils.console.print(f"{proj}: updated on {projects[proj]}")
        else:
            LOG.info("There are no busy projects at the moment.")
