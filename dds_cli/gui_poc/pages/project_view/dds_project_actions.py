"""DDS Project Actions Widget"""
from typing import Any
from textual.app import ComposeResult
from textual.widgets import TabPane, Label, TabbedContent
from dds_cli.gui_poc.components.dds_container import DDSContainer


class DDSProjectActions(DDSContainer):
    """A widget for the project actions."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

    def compose(self) -> ComposeResult:
       with TabbedContent():
           with TabPane("Download data", id="download-data"):
               yield Label("Download")
           with TabPane("User Access", id="user-access"):
               yield Label("User Access")
