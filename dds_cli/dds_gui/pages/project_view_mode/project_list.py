"""DDS Project List Widget"""

from textual import events
from textual.app import ComposeResult
from textual.widgets import Select

from dds_cli.dds_gui.components.dds_button import DDSButton
from dds_cli.dds_gui.components.dds_container import DDSContainer, DDSSpacedContainer
from dds_cli.dds_gui.components.dds_select import DDSSelect
from dds_cli.dds_gui.components.dds_text_item import DDSTextItem


class ProjectList(DDSContainer):
    """A widget for the project list selection."""

    def compose(self) -> ComposeResult:
        with DDSSpacedContainer():
            yield DDSTextItem(
                "Select a project to view the project content, information, invite users, and upload and download data."
            )
            yield DDSSelect(
                title="Select a project",
                data=self.app.projects_id,
                value=(
                    self.app.selected_project_id if self.app.selected_project_id else Select.BLANK
                ),
            )
            yield DDSButton("View Project", id="view-project")

    def on_button_pressed(self, event: events.Click) -> None:
        """Handle button presses."""
        if event.button.id == "view-project":
            selected_project_id = self.query_one(DDSSelect).value
            if selected_project_id is Select.BLANK:
                self.app.set_selected_project_id(None)
            else:
                self.app.set_selected_project_id(selected_project_id)
