"""DDS Project Information Widget"""

from dataclasses import dataclass
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

from dds_cli.base import DDSBaseClass
from dds_cli.dds_gui.types.dds_status_types import DDSStatus


@dataclass
class ProjectInformationDataTable:
    """A dataclass for the project information table."""

    status: DDSStatus
    created_by: str
    last_updated: str
    size: str
    pi: str

    @staticmethod
    def from_dict(data: dict) -> "ProjectInformationDataTable":
        print(data)
        return ProjectInformationDataTable(
            status=DDSStatus(data["Status"]),
            created_by=data["Created by"],
            last_updated=data["Last updated"],
            size=str(data["Size"]),
            pi=data["PI"],
        )

@dataclass
class ProjectInformationData:
    """A dataclass for the project information."""

    name: str
    description: str

    information_table: ProjectInformationDataTable

    @staticmethod
    def from_dict(data: dict) -> "ProjectInformationData":
        return ProjectInformationData(
            name=data["Title"],
            description=data["Description"],
            information_table=ProjectInformationDataTable.from_dict(data),
        )

class ProjectInformation(DDSContainer):
    """A widget for the project information."""

    project_id = "someunit00002"

    project_information =  ProjectInformationData.from_dict(data = DDSBaseClass(project=project_id).get_project_info())

    DEFAULT_CSS = """
    DDSSpacedContainer:first-of-type > * {
        padding-right: 1;
    }
    
    """

    def compose(self) -> ComposeResult:
        if self.project_information:
            with DDSSpacedContainer():
                with DDSContentContainer():
                    yield Label(
                        f"[b]Project Title:[/b] {self.project_information.name}",
                        id="project-title",
                    )
                    yield Label(
                        f"[b]Project Description:[/b] {self.project_information.description}",
                        id="project-description",
                    )
                yield ProjectInformationTable(
                    self.project_information.information_table, id="project-information-table"
                )
        else:
            yield Label("No project selected")


class ProjectInformationTable(Widget):
    """A widget for the project information table."""

    def __init__(self, data: ProjectInformationDataTable, *args: Any, **kwargs: Any) -> None:
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
                Static("PI", classes="key-pair-row-key"),
                Static(self.data.pi, classes="key-pair-row-value"),
                classes="key-pair-row",
            )
