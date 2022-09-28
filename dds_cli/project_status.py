"""Data Delivery System Project Status manager."""
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


class ProjectStatusManager(base.DDSBaseClass):
    """Project Status manager class."""

    def __init__(
        self,
        project: str,
        no_prompt: bool = False,
        token_path: str = None,
    ):
        """Handle actions regarding project status in the cli."""
        # Initiate DDSBaseClass to authenticate user
        super().__init__(
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
            except ValueError as err:
                raise exceptions.ApiResponseError(
                    f"Time zone mismatch: Incorrect zone '{current_deadline.split()[-1]}'"
                )
            else:
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
                except ValueError as err:
                    raise exceptions.ApiResponseError(
                        f"Time zone mismatch: Incorrect zone '{row[1].split()[-1]}'"
                    )
                else:
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

        response_json, _ = dds_cli.utils.perform_request(
            endpoint=DDSEndpoint.UPDATE_PROJ_STATUS,
            headers=self.token,
            method="post",
            params={"project": self.project},
            json=extra_params,
            error_message="Failed to update project status",
        )

        dds_cli.utils.console.print(f"Project {response_json.get('message')}")


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
                LOG.info(f"There are {num_busy} busy projects at the moment.")
            else:
                projects: typing.Dict = response_json.get("projects")
                LOG.info(f"The following projects are busy:")
                for p in projects:
                    dds_cli.utils.console.print(f"{p}: updated on {projects[p]}")
        else:
            LOG.info(f"There are no busy projects at the moment.")
