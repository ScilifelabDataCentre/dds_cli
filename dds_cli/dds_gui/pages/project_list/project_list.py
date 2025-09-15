"""DDS Project List Widget"""

from typing import List
from textual import events
from textual.app import ComposeResult
from textual.widgets import Select, LoadingIndicator, Label
from textual.reactive import reactive

from dds_cli.dds_gui.components.dds_button import DDSButton
from dds_cli.dds_gui.components.dds_container import DDSContainer, DDSSpacedContainer
from dds_cli.dds_gui.components.dds_select import DDSSelect
from dds_cli.dds_gui.components.dds_text_item import DDSTextItem


class ProjectList(DDSContainer):
    """A widget for the project list selection."""

    # Local reactive attributes that mirror app state and trigger recomposition
    project_list: reactive[List[dict]] = reactive(None, recompose=True)
    projects_loading: reactive[bool] = reactive(False, recompose=True)
    auth_status: reactive[bool] = reactive(False, recompose=True)

    def compose(self) -> ComposeResult:
        with DDSSpacedContainer():
            yield DDSTextItem(
                "Select a project to view the project content, information, invite users, and upload and download data."
            )
            
            if not self.auth_status:
                # Show message when not authenticated
                yield Label("Please authenticate to view projects")
            elif self.projects_loading:
                # Show loading indicator when fetching projects
                yield LoadingIndicator()
            elif self.project_list:
                # Show project selector when projects are loaded
                yield DDSSelect(
                    title="Select a project",
                    data=self.extract_project_ids(),
                    value=(
                        self.app.selected_project_id if self.app.selected_project_id else Select.BLANK
                    ),
                    disabled=not self.auth_status,
                )
                yield DDSButton(
                    "View Project",
                    id="view-project",
                    disabled=not self.auth_status,
                )
            else:
                # Show message when no projects found
                yield Label("No projects found")

    def on_mount(self) -> None:
        """On mount, sync initial state and set up watchers."""
        self.project_list = self.app.project_list
        self.projects_loading = self.app.projects_loading
        self.auth_status = self.app.auth_status

    def watch_project_list(self, project_list: List[dict]) -> None:
        """Watch for changes in project list."""
        self.project_list = project_list

    def watch_projects_loading(self, projects_loading: bool) -> None:
        """Watch for changes in projects loading state."""
        self.projects_loading = projects_loading

    def watch_auth_status(self, auth_status: bool) -> None:
        """Watch for changes in auth status."""
        self.auth_status = auth_status

    def on_button_pressed(self, event: events.Click) -> None:
        """Handle button presses."""
        if event.button.id == "view-project":
            value = self.query_one(DDSSelect).value
            if value is Select.BLANK:
                self.app.set_selected_project_id(None)
                self.notify(
                    "Please select a project to view project content and information.",
                    severity="warning",
                )
            else:
                self.app.set_selected_project_id(value)

    def extract_project_ids(self) -> List[str]:
        """Extract the project IDs from the project list."""
        return [
            p["Project ID"]
            for p in self.project_list or []
            if ("Project ID" in p and isinstance(p["Project ID"], str) and p["Project ID"].strip())
        ]
