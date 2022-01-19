"""Data Delivery System Project Creator."""
import logging

# Installed
import requests
import simplejson

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


class ProjectCreator(base.DDSBaseClass):
    """Project creator class."""

    def __init__(
        self,
        username: str,
        method: str = "create",
        no_prompt: bool = False,
    ):
        """Handle actions regarding project creation in the cli."""
        # Initiate DDSBaseClass to authenticate user
        super().__init__(username=username, method=method, no_prompt=no_prompt)

        # Only method "create" can use the ProjectCreator class
        if self.method != "create":
            raise exceptions.AuthenticationError(f"Unauthorized method: '{self.method}'")

    # Public methods ###################### Public methods #
    def create_project(self, title, description, principal_investigator, sensitive, users_to_add):
        """Create project with title and description."""
        # Submit request to API
        try:
            response = requests.post(
                DDSEndpoint.CREATE_PROJ,
                headers=self.token,
                json={
                    "title": title,
                    "description": description,
                    "pi": principal_investigator,
                    "is_sensitive": sensitive,
                    "users_to_add": users_to_add,
                },
            )
        except requests.exceptions.RequestException as err:
            raise exceptions.ApiRequestError(message=str(err))

        # Error if failed
        if not response.ok:
            raise exceptions.ProjectCreationError(response.json().get("message"))

        # Get response info as json
        try:
            project_info = response.json()
        except simplejson.JSONDecodeError as err:
            raise exceptions.ApiResponseError(err)

        return project_info.get("project_id"), project_info.get("user_addition_statuses")
