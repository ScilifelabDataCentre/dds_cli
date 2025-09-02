"""DDS Project List Widget"""

from typing import List
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
                data=self.extract_project_ids(),
                value=(
                    self.app.selected_project_id if self.app.selected_project_id else Select.BLANK
                ),
                disabled=not self.app.auth_status,
            )
            yield DDSButton(
                "View Project",
                id="view-project",
                disabled=not self.app.auth_status,
            )

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
            for p in self.app.project_list or []
            if ("Project ID" in p and isinstance(p["Project ID"], str) and p["Project ID"].strip())
        ]
