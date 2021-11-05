import logging
import pathlib

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
        username: str = None,
        method: str = "create",
    ):

        # Initiate DDSBaseClass to authenticate user
        super().__init__(username=username, method=method)

        # Only method "create" can use the ProjectCreator class
        if self.method != "create":
            raise exceptions.AuthenticationError(f"Unauthorized method: '{self.method}'")

    # Public methods ###################### Public methods #
    def create_project(self, title, description, principal_investigator, sensitive):
        """Creates project with title and description"""

        # Variables
        created = False
        error = ""
        created_project_id = ""

        # Submit request to API
        try:
            response = requests.post(
                DDSEndpoint.CREATE_PROJ,
                headers=self.token,
                json={
                    "title": title,
                    "description": description,
                    "pi": principal_investigator,
                    "sensitive": sensitive,
                },
            )
        except requests.exceptions.RequestException as err:
            raise exceptions.ApiRequestError(message=str(err))
        else:
            # Error if failed
            if not response.ok:
                error = f"{response.json().get('message')}"
                LOG.error(error)
                return created, created_project_id, error

            try:
                created, created_project_id, error = (
                    True,
                    response.json().get("project_id"),
                    response.json().get("message"),
                )
            except simplejson.JSONDecodeError as err:
                error = str(err)
                LOG.warning(error)

        return created, created_project_id, error
