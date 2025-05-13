"""DDS Project Actions Widget"""
from typing import Any
from textual.app import ComposeResult
from textual.widgets import TabPane, Label, TabbedContent
from dds_cli.gui_poc.components.dds_container import DDSContainer, DDSContentContainer
from dds_cli.gui_poc.pages.project_view.project_actions.download_data import DownloadData
from dds_cli.gui_poc.pages.project_view.project_actions.user_access import UserAccess


class DDSProjectActions(DDSContainer):
    """A widget for the project actions."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

    DEFAULT_CSS = """
    TabbedContent {
        border: round $secondary;
        height: 100%;
    }
    """

    def compose(self) -> ComposeResult:
       with TabbedContent():
           with TabPane("Download data", id="download-data"):
                yield DownloadData()
           with TabPane("User Access", id="user-access"):
               yield UserAccess()
