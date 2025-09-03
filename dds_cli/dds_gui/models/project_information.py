"""Dataclasses for the project information."""

import dataclasses

from dds_cli.dds_gui.types.dds_status_types import DDSStatus


def size_to_str(size: str | None) -> str:
    """Convert a size to a string.
    Args:
        size: The size in B.

    Returns:
        The size as a string with a unit prefix.
    """
    if size is None:
        return "N/A"
    if size >= 1000:
        return str(size / 1000) + " KB"
    if size >= 1000000:
        return str(size / 1000000) + " MB"
    if size >= 1000000000:
        return str(size / 1000000000) + " GB"
    if size >= 1000000000000:
        return str(size / 1000000000000) + " TB"

    return str(size) + " B"


@dataclasses.dataclass
class ProjectInformationDataTable:
    """A dataclass for the project information table."""

    status: DDSStatus
    created_by: str
    last_updated: str
    size: str
    pi: str  # pylint: disable=invalid-name

    @staticmethod
    def from_dict(data: dict) -> "ProjectInformationDataTable":
        """Create a ProjectInformationDataTable instance from dictionary data."""
        # Validate required fields
        required_fields = ["Status", "Created by", "Last updated", "Size", "PI"]
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")

        # Handle size field - convert to string if not None, otherwise use "N/A"
        size_value = data["Size"]
        size_str = size_to_str(size_value)

        return ProjectInformationDataTable(
            status=DDSStatus(data["Status"]),
            created_by=data["Created by"] or "N/A",
            last_updated=data["Last updated"] or "N/A",
            size=size_str,
            pi=data["PI"] or "N/A",
        )


@dataclasses.dataclass
class ProjectInformationData:
    """A dataclass for the project information."""

    name: str
    description: str

    information_table: ProjectInformationDataTable

    @staticmethod
    def from_dict(data: dict) -> "ProjectInformationData":
        """Create a ProjectInformationData instance from dictionary data."""
        # Validate required fields
        required_fields = ["Title", "Description"]
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")

        return ProjectInformationData(
            name=data["Title"] or "N/A",
            description=data["Description"] or "N/A",
            information_table=ProjectInformationDataTable.from_dict(data),
        )
