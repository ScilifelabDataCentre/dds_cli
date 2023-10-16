"""Data Delivery System Project Status manager."""
import datetime
import logging
import typing
import sys

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
            method_check=False,
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

    def extend_deadline(self):
        extra_params = {"send_email": False}

        # make a first call to fetch the project status and default deadline
        response_json, _ = dds_cli.utils.perform_request(
            endpoint=DDSEndpoint.UPDATE_PROJ_STATUS,
            headers=self.token,
            method="patch",
            params={"project": self.project},
            json=extra_params,
        )

        dds_cli.utils.console.print(
            "You are about to extend the deadline of the following project:\n\n"
        )
        table = self.generate_project_table(project_info=response_json.get("project_info"))
        dds_cli.utils.console.print(table)

        default_unit_days = response_json.get("default_unit_days")
        current_deadline = response_json.get("project_status").get("current_deadline")
        print_info = f"\n\nCurrent deadline: [b][green]{current_deadline}[/green][/b]\n"
        print_info += (
            f"Default deadline extension: [b][green]{default_unit_days}[/green][/b] days\n"
        )
        dds_cli.utils.console.print(print_info)

        answered = False
        while not answered:
            prompt_question = f"Enter the number of days you want to extend the project, the number of days has to be equal or same as [b][green]{response_json.get('default_unit_days')}[/green][/b].\n"
            prompt_question += f"Or leave it empty to apply the default [b][green]{response_json.get('default_unit_days')} days [/green][/b]"
            extend_deadline = rich.prompt.Prompt.ask(prompt_question)
            try:
                if extend_deadline == "" or int(extend_deadline) < response_json.get(
                    "default_unit_days"
                ):
                    break
                else:
                    dds_cli.utils.console.print(
                        "\n[b][red]The number of days has to be lower than the default deadline extension number[/b][/red]\n"
                    )
            except:
                dds_cli.utils.console.print(
                    "\n[b][red]Remember to write the number of days using numbers (dont use letters)[/b][/red]\n"
                )
                continue
        extend_deadline = int(extend_deadline or default_unit_days)

        print_info = f"\n\n[b][blue]Are you sure [/b][/blue]you want to perform this operation?. "
        print_info += (
            f"\nThis will extend the deadline by [b][blue]{extend_deadline} days[/b][/blue]."
        )
        print_info += "\nYou can only extend the data availability a maximun of [b][blue]3 times[/b][/blue], this consumes one of those times."
        if not rich.prompt.Confirm.ask(print_info):
            LOG.info("Probably for the best. Exiting.")
            sys.exit(0)

        # TODO second call with confirmed flag


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
            method_check=False,
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
