"""DDS State Manager"""

from textual.app import App
from textual.reactive import reactive

from dds_cli.auth import Auth
from dds_cli.data_lister import DataLister
from dds_cli.dds_gui.models.project import ProjectContentData
from dds_cli.exceptions import ApiRequestError, ApiResponseError

class DDSStateManager(App):
    """
    State manager for the DDS CLI. Consists of reactive states available app wide.

    Reactive attributes are used to update the UI, fetch data, set new states, etc.
    Reactive attributes are recomposed when the state changes,
    triggering re-renders and re-computations of the derived states.

    Derived states are attributes computed based on the reactive attributes.
    When the reactive attributes are updated, the derived states are automatically updated.

    Setters are used to avoid pylint warnings about attribute-defined-outside-init.
    Functionally, the reactive attributes can be set in the child classes,
    but are set here for consistence over the app, instead of ignoring the pylint warnings.
    """

    #### TOKEN PATH #########################################################

    # TODO: Make this get the token path correctly
    token_path = "~/.dds_cli_token"

    #### AUTH ################################################################

    auth: reactive[Auth] = reactive(Auth(authenticate=False, token_path=token_path), recompose=True)
    auth_status: reactive[bool] = reactive(False, recompose=True)

    def set_auth_status(self, new_auth_status: bool) -> None:
        """Set the auth status."""
        self.auth_status = new_auth_status

    #### PROJECT LISTING ####################################################

    projects: reactive[list[str]] = reactive(None, recompose=True)
    project_ids: reactive[list[str]] = reactive(None, recompose=True)
    selected_project_id: reactive[str] = reactive(None, recompose=True)

    def fetch_projects(self) -> list[str]:
        """Fetch the projects."""
        self.projects = DataLister(json=True).list_projects()

    def compute_project_ids(self) -> list[str]:
        """Compute the project ids."""
        return [project["Project ID"] for project in self.projects] if self.projects else []

    def set_selected_project_id(self, project_id: str) -> None:
        """Set the selected project id."""
        self.selected_project_id = project_id

    #### PROJECT CONTENT #####################################################

    project_content: reactive[ProjectContentData] = reactive(None, recompose=True)

    def compute_project_content(self) -> ProjectContentData | None:
        """Compute the project content."""

        if self.selected_project_id:
            project_content = DataLister(
                json=True, tree=True, project=self.selected_project_id
            ).list_recursive()
            return ProjectContentData.from_dict(
                project_content, project_name=self.selected_project_id
            )
        else:
            return None

    #### WATCHERS ###########################################################

    def watch_auth_status(self, auth_status: bool) -> None:
        """Watch the auth status."""
        if auth_status:
            # Fetch the projects when the auth status is True.
            # This is to ensure that the projects are fetched when the user is authenticated only.
            # If called without auth status, recursion error occurs and/or the base class will try to authenticate in the CLI.
            try:
                self.fetch_projects()
            except (ApiRequestError, ApiResponseError) as err:
                self.notify(f"Failed to fetch projects: {err}", severity="error")
                self.projects = None
        else:
            self.projects = None
            self.selected_project_id = None
