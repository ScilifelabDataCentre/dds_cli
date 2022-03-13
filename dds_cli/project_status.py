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
        try:
            response = requests.get(
                DDSEndpoint.UPDATE_PROJ_STATUS,
                headers=self.token,
                params={"project": self.project},
                json={"history": show_history},
                timeout=DDSEndpoint.TIMEOUT,
            )
        except requests.exceptions.RequestException as err:
            raise exceptions.ApiRequestError(message=str(err))

        # Check response
        if not response.ok:
            raise exceptions.APIError(f"Failed to get any projects: {response.text}")

        # Get result from API
        try:
            resp_json = response.json()
        except simplejson.JSONDecodeError as err:
            raise exceptions.APIError(f"Could not decode JSON response: {err}")
        else:
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
        try:
            response = requests.post(
                DDSEndpoint.UPDATE_PROJ_STATUS,
                headers=self.token,
                params={"project": self.project},
                json=extra_params,
                timeout=DDSEndpoint.TIMEOUT,
            )
        except requests.exceptions.RequestException as err:
            raise exceptions.ApiRequestError(message=str(err))

        # Check response
        if not response.ok:
            raise exceptions.APIError(f"An Error occured: {response.json().get('message')}")

        # Get result from API
        try:
            resp_json = response.json()
        except simplejson.JSONDecodeError as err:
            raise exceptions.APIError(f"Could not decode JSON response: {err}")
        else:
            dds_cli.utils.console.print(f"Project {resp_json.get('message')}")
