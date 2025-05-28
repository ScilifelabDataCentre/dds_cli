"""Types for the status of the project."""

from enum import Enum


class DDSStatus(Enum):
    """Enum for the status of the project."""

    AVAILABLE = "Available"
    IN_PROGRESS = "In Progress"
    DELETED = "Deleted"
    EXPIRED = "Expired"
    ARCHIVED = "Archived"
    ABORTED = "Aborted"
