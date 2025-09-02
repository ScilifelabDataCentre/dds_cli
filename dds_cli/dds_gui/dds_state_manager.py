"""DDS State Manager"""

import pathlib
from typing import List
from textual.app import App
from textual import work
from textual.reactive import reactive

import dds_cli.auth
import dds_cli.data_lister
import dds_cli.exceptions
import dds_cli.project_info

from dds_cli.dds_gui.models.project import ProjectContentData
from dds_cli.dds_gui.models.project_information import ProjectInformationData


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

    # Default token path for CLI authentication token
    token_path = str(pathlib.Path.home() / ".dds_cli_token")

    #### AUTH ################################################################

    auth: reactive[dds_cli.auth.Auth] = reactive(
        dds_cli.auth.Auth(authenticate=False, token_path=token_path), recompose=True
    )
    auth_status: reactive[bool] = reactive(False, recompose=True)

    def set_auth_status(self, new_auth_status: bool) -> None:
        """Set the auth status."""
        self.auth_status = new_auth_status

    #### PROJECT LISTING ####################################################

    project_list: reactive[List[dict]] = reactive(None, recompose=True)
    selected_project_id: reactive[str] = reactive(None, recompose=True)

    def fetch_projects(self) -> List[str]:
        """Fetch the projects and automatically compute project_ids via reactive watcher."""
        self.project_list: List[dict] = dds_cli.data_lister.DataLister(json=True).list_projects()

    def set_selected_project_id(self, project_id: str) -> None:
        """Set the selected project id."""
        self.selected_project_id = project_id

    #### PROJECT CONTENT #####################################################

    project_content: reactive[ProjectContentData] = reactive(None, recompose=True)
    is_loading: reactive[bool] = reactive(False, recompose=True)

    @work(exclusive=True, thread=True)
    def load_project_content(self, project_id: str) -> None:
        """Background worker to fetch project content for a project id.
        This solution was proposed to avoid unnecessary re-renders of the project
        content widget while still keeping the label reactive.
        Reference: https://textual.textualize.io/guide/workers/
        """
        try:
            project_content = dds_cli.data_lister.DataLister(
                json=True, project=project_id
            ).list_recursive()
        except (
            dds_cli.exceptions.ApiRequestError,
            dds_cli.exceptions.ApiResponseError,
            dds_cli.exceptions.DDSCLIException,
        ) as err:
            self.call_from_thread(self._on_project_content_error, project_id, str(err), "error")
            return
        except dds_cli.exceptions.NoDataError as data_err:
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

    #### PROJECT INFORMATION #################################################

    project_information: reactive[ProjectInformationData] = reactive(None, recompose=True)

    def fetch_project_information(self, project_id: str) -> None:
        """Fetch the project information for a project id."""
        try:
            self.project_information = ProjectInformationData.from_dict(
                dds_cli.project_info.ProjectInfoManager(project=project_id).get_project_info()
            )
        except (
            dds_cli.exceptions.ApiRequestError,
            dds_cli.exceptions.ApiResponseError,
            dds_cli.exceptions.DDSCLIException,
        ) as err:
            self.notify(f"Failed to fetch project information: {err}", severity="error")
            self.project_information = None

    #### WATCHERS ###########################################################

    def watch_auth_status(self, auth_status: bool) -> None:
        """Watch the auth status."""
        if auth_status:
            # Fetch the projects when the auth status is True.
            # This is to ensure that the projects are fetched when the user is authenticated only.
            # If called without auth status, recursion error occurs and/or the base class
            #  will try to authenticate in the CLI.
            try:
                self.fetch_projects()
            except (
                dds_cli.exceptions.ApiRequestError,
                dds_cli.exceptions.ApiResponseError,
                dds_cli.exceptions.DDSCLIException,
            ) as err:
                self.notify(f"Failed to fetch projects: {err}", severity="error")
                self.project_list = None  # This triggers watch_projects to clear project_ids
        else:
            self.project_list = None  # This triggers watch_projects to clear project_ids
            self.selected_project_id = None

    def watch_selected_project_id(self, selected_project_id: str) -> None:
        """Start loading project content when the selected project changes."""
        # Clear current content and information when switching projects
        self.project_information = None
        self.project_content = None

        if not selected_project_id:
            self.is_loading = False
            return

        # Get project information
        self.fetch_project_information(selected_project_id)

        # Start loading project content
        self.is_loading = True
        self.load_project_content(selected_project_id)
