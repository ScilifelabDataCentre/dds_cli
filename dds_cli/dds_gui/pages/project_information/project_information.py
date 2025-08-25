"""DDS Project Information Widget"""

from typing import Any
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widget import Widget
from textual.widgets import Label, Static

from dds_cli.dds_gui.components.dds_container import (
    DDSContainer,
    DDSContentContainer,
    DDSSpacedContainer,
)
from dds_cli.dds_gui.components.dds_status_chip import DDSStatusChip
from dds_cli.dds_gui.dds_state_manager import ProjectInformation as ProjectInformationType


class ProjectInformation(DDSContainer):
    """A widget for the project information."""

    def compose(self) -> ComposeResult:
        if self.app.selected_project_id:
            with DDSSpacedContainer():
                with DDSContentContainer():
                    yield Label(
                        f"[b]Project Title:[/b] {self.app.project_information.name}",
                        id="project-title",
                    )
                    yield Label(
                        f"[b]Project Description:[/b] {self.app.project_information.description}",
                        id="project-description",
                    )
                yield ProjectInformationTable(
                    self.app.project_information, id="project-information-table"
                )
        else:
            yield Label("No project selected")


class ProjectInformationTable(Widget):
    """A widget for the project information table."""

    def __init__(self, data: ProjectInformationType, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.data = data

    DEFAULT_CSS = """
    .key-pair-table {
        width: 100%;
    }
    .key-pair-row {
        width: 100%;
        height: auto;
        border-bottom: solid $primary;
    }

    .key-pair-row:last-of-type {
        border-bottom: none;
        padding-bottom: 0;
    }
    .key-pair-row-key {
        text-style: bold;
        width: 50%;
    }
    .key-pair-row-value {
        text-align: right;
        align: right middle;
        width: 50%;
    }
    
    """

    def compose(self) -> ComposeResult:
        with Vertical(classes="key-pair-table"):
            yield Horizontal(
                Static("Status", classes="key-pair-row-key"),
                DDSStatusChip(self.data.status, classes="key-pair-row-value"),
                classes="key-pair-row",
            )
            yield Horizontal(
                Static("Created By", classes="key-pair-row-key"),
                Static(self.data.created_by, classes="key-pair-row-value"),
                classes="key-pair-row",
            )
            yield Horizontal(
                Static("Last Updated", classes="key-pair-row-key"),
                Static(self.data.last_updated, classes="key-pair-row-value"),
                classes="key-pair-row",
            )
            yield Horizontal(
                Static("Size", classes="key-pair-row-key"),
                Static(self.data.size, classes="key-pair-row-value"),
                classes="key-pair-row",
            )
            yield Horizontal(
                Static("Support Contact", classes="key-pair-row-key"),
                Static(self.data.support_contact, classes="key-pair-row-value"),
                classes="key-pair-row",
            )
