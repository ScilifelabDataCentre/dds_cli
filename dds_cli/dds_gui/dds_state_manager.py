"""DDS State Manager"""

from typing import List
from textual.app import App
from textual import work
from textual.reactive import reactive

from dds_cli.auth import Auth
from dds_cli.data_lister import DataLister
from dds_cli.dds_gui.models.project import ProjectContentData
from dds_cli.exceptions import ApiRequestError, ApiResponseError, DDSCLIException, NoDataError


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

    projects: reactive[List[str]] = reactive(None, recompose=True)
    project_ids: reactive[List[str]] = reactive(None, recompose=True)
    selected_project_id: reactive[str] = reactive(None, recompose=True)

    def fetch_projects(self) -> List[str]:
        """Fetch the projects and automatically compute project_ids via reactive watcher."""
        self.projects = DataLister(json=True).list_projects()
        # project_ids will be computed automatically by watch_projects()

    def _extract_project_ids(self) -> List[str]:
        """Extract project IDs with validation.

        Note: Named with underscore to avoid Textual's computed property behavior.
        If named compute_project_ids, it would make project_ids read-only.
        """
        if not self.projects:
            return []

        # Extract project IDs with validation for malformed data
        project_ids = []
        for project in self.projects:
            project_id = project.get("Project ID")
            if project_id and isinstance(project_id, str) and project_id.strip():
                project_ids.append(project_id)

        return project_ids

    def set_selected_project_id(self, project_id: str) -> None:
        """Set the selected project id."""
        self.selected_project_id = project_id

    #### PROJECT CONTENT #####################################################

    project_content: reactive[ProjectContentData] = reactive(None, recompose=True)
    is_loading: reactive[bool] = reactive(False, recompose=True)

    def watch_selected_project_id(self, selected_project_id: str) -> None:
        """Start loading project content when the selected project changes."""
        # Clear current content when switching projects
        self.project_content = None

        if not selected_project_id:
            self.is_loading = False
            return

        # Start loading
        self.is_loading = True
        self.load_project_content(selected_project_id)

    @work(exclusive=True, thread=True)
    def load_project_content(self, project_id: str) -> None:
        """Background worker to fetch project content for a project id.
        This solution was proposed to avoid unnecessary re-renders of the project
        content widget while still keeping the label reactive.
        Reference: https://textual.textualize.io/guide/workers/
        """
        try:
            project_content = DataLister(json=True, tree=True, project=project_id).list_recursive()
        except (ApiRequestError, ApiResponseError, DDSCLIException) as err:
            self.call_from_thread(self._on_project_content_error, project_id, str(err), "error")
            return
        except NoDataError as data_err:
            self.call_from_thread(
                self._on_project_content_error, project_id, str(data_err), "warning"
            )
            return

        content = ProjectContentData.from_dict(project_content, project_name=project_id)
        self.call_from_thread(self._on_project_content_loaded, content)

    def _on_project_content_loaded(self, content: ProjectContentData) -> None:
        """Handle successful content load on the main thread."""
        self.is_loading = False
        self.project_content = content

    def _on_project_content_error(self, project_id: str, message: str, severity: str) -> None:
        """Handle content load error on the main thread."""
        self.is_loading = False
        if severity == "warning":
            self.notify(f"No data found for project {project_id}: {message}", severity="warning")
        else:
            self.notify(f"Failed to fetch project content: {message}", severity="error")
        if self.selected_project_id == project_id:
            self.project_content = None

    #### WATCHERS ###########################################################

    def watch_projects(self, projects: List[dict]) -> None:
        """Automatically compute project_ids when projects change.

        This is the key to the reactive pattern - when projects data changes,
        project_ids is automatically recomputed and UI updates follow.
        """
        if projects is not None:
            # Projects was fetched (could be empty list or list with data)
            self.project_ids = self._extract_project_ids()
        else:
            # Projects is None (not fetched or cleared)
            self.project_ids = None

    def watch_auth_status(self, auth_status: bool) -> None:
        """Watch the auth status."""
        if auth_status:
            # Fetch the projects when the auth status is True.
            # This is to ensure that the projects are fetched when the user is authenticated only.
            # If called without auth status, recursion error occurs and/or the base class
            #  will try to authenticate in the CLI.
            try:
                self.fetch_projects()
            except (ApiRequestError, ApiResponseError, DDSCLIException) as err:
                self.notify(f"Failed to fetch projects: {err}", severity="error")
                self.projects = None  # This triggers watch_projects to clear project_ids
        else:
            self.projects = None  # This triggers watch_projects to clear project_ids
            self.selected_project_id = None
