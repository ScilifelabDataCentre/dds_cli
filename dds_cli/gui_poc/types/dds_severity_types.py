"""Types for the severity of the DDS."""

from enum import Enum


class DDSSeverity(Enum):
    """Severity of the DDS GUI alerts."""

    DEFAULT = "default"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
