"""Data Delivery System Project Creator."""
import logging

# Installed
import requests
import simplejson
import rich.prompt

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
        method: str = "create",
        no_prompt: bool = False,
        token_path: str = None,
    ):
        """Handle actions regarding project creation in the cli."""
        # Initiate DDSBaseClass to authenticate user
        super().__init__(method=method, no_prompt=no_prompt, token_path=token_path)

        # Only method "create" can use the ProjectCreator class
        if self.method != "create":
            raise exceptions.AuthenticationError(f"Unauthorized method: '{self.method}'")

    # Public methods ###################### Public methods #
    def create_project(
        self, title, description, principal_investigator, non_sensitive, users_to_add, force=False
    ):
        """Create project with title and description."""
        # Variables
        created = False
        error = ""
        created_project_id = ""
        user_addition_statuses = {}

        # Submit request to API
        try:
            response = requests.post(
                DDSEndpoint.CREATE_PROJ,
                headers=self.token,
                json={
                    "title": title,
                    "description": description,
                    "pi": principal_investigator,
                    "non_sensitive": non_sensitive,
                    "users_to_add": users_to_add,
                    "force": force,
                },
                timeout=DDSEndpoint.TIMEOUT,
            )
        except requests.exceptions.RequestException as err:
            raise exceptions.ApiRequestError(message=str(err))
        else:
            # Error if failed
            if not response.ok:
                message = response.json().get("message")
                title = response.json().get("title")
                description = response.json().get("description")
                pi = response.json().get("pi")
                email = response.json().get("email")

                messages = [message, title, description, pi, email]

                error = next(message for message in messages if message)

                if isinstance(error, list):
                    error = error[0]

                if "Insufficient credentials" in error:
                    error = "You do not have the required permissions to create a project."
                LOG.error(error)
                return created, created_project_id, user_addition_statuses, error

            warning_message = response.json().get("warning")

            if warning_message:
                if self.no_prompt:
                    LOG.warning(
                        f"{warning_message}\n\n`--no-prompt` option used: Not creating project."
                    )
                    proceed_creation = False
                else:
                    proceed_creation = rich.prompt.Confirm.ask(
                        f"[red][bold]WARNING!![/bold][/red] {warning_message}"
                        "\n\nAre you sure you wish to create this project anyway?"
                    )

                if not proceed_creation:
                    return created, created_project_id, user_addition_statuses, error

                return self.create_project(
                    title=title,
                    description=description,
                    principal_investigator=principal_investigator,
                    non_sensitive=non_sensitive,
                    users_to_add=users_to_add,
                    force=True,
                )

            try:
                created, created_project_id, user_addition_statuses, error = (
                    True,
                    response.json().get("project_id"),
                    response.json().get("user_addition_statuses"),
                    response.json().get("message"),
                )
            except simplejson.JSONDecodeError as err:
                error = str(err)
                LOG.warning(error)

        return created, created_project_id, user_addition_statuses, error
