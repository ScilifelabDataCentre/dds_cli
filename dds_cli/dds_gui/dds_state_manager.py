"""DDS State Manager"""

from textual.reactive import reactive

from dds_cli.auth import Auth
from dds_cli.data_lister import DataLister


class DDSStateManager:
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

    #### WATCHERS ###########################################################

    def watch_auth_status(self, auth_status: bool) -> None:
        """Watch the auth status."""
        if auth_status:
            # Fetch the projects when the auth status is True.
            # This is to ensure that the projects are fetched when the user is authenticated only.
            # If called on app initialization, recursion error occurs.
            self.fetch_projects()
        else:
            self.projects = None
            self.selected_project_id = None
