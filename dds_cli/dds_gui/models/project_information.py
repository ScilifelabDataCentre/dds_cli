"""Dataclasses for the project information."""

from dataclasses import dataclass

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
        """Create a ProjectInformationDataTable instance from dictionary data."""
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
        """Create a ProjectInformationData instance from dictionary data."""
        return ProjectInformationData(
            name=data["Title"],
            description=data["Description"],
            information_table=ProjectInformationDataTable.from_dict(data),
        )