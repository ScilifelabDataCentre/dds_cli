"""DDS Project Information Widget"""

from textual.app import ComposeResult
from textual.widgets import Label
from dds_cli.gui_poc.components.dds_container import (
    DDSContainer,
    DDSContentContainer,
    DDSSpacedContainer,
)
from dds_cli.gui_poc.components.dds_key_pair_table import DDSKeyPairTable

class ProjectInformation(DDSContainer):
    """A widget for the project information."""

    def compose(self) -> ComposeResult:
        if self.app.selected_project_id:
            with DDSSpacedContainer():
                with DDSContentContainer():
                    yield Label("[b]Project Title:[/b] Test Title", id="project-title")
                yield Label("[b]Project Description:[/b] Test Description")
            yield DDSKeyPairTable(self.app.project_information, id="project-information-table")
        else:
            yield Label("No project selected")

    def watch_project_id(self, project_id: str) -> None:
        """Watch the project id state and update the project information."""
        self.query_one("project-title").update(f"[b]Project Title:[/b] {project_id}")
