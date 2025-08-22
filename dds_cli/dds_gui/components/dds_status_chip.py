"""DDS Status Chip"""

from typing import Any
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static

from dds_cli.dds_gui.types.dds_status_types import DDSStatus


class DDSStatusChip(Widget):
    """A widget for the status of the project."""

    def __init__(self, status: DDSStatus, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.status = status

    DEFAULT_CSS = """
    #status-chip {
        height: auto;
        width: auto;
        padding: 0 1;
        text-align: center;
        text-style: bold;
    }

    .available {
        background: #A0FF77;
        color: #184305;
    }   

    .in-progress {
        background: #D0B3FE;
        color: #330183;
    }   

    .deleted {
        background: #F8B4B4;
        color: #700000;
    }   

    .expired {
        background: #F8FE55;
        color: #4F5205;
    }   

    .archived {
        background: #B4B4B4;
        color: #1C1C1C;
    }

    .aborted {
        background: #FFBA6B;
        color: #5F2607;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static(
            self.status.value, classes=self.status.value.lower().replace(" ", "-"), id="status-chip"
        )
