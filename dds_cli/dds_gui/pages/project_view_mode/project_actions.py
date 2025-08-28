"""DDS Project Actions Widget"""

from textual.app import ComposeResult
from textual.widgets import TabPane, TabbedContent
from dds_cli.dds_gui.components.dds_container import DDSContainer
from dds_cli.dds_gui.pages.project_view_mode.project_actions_tabs.download_data import DownloadData
from dds_cli.dds_gui.pages.project_view_mode.project_actions_tabs.user_access import UserAccess


class ProjectActions(DDSContainer):
    """Widget contianing tabbed content for the project actions."""

    DEFAULT_CSS = """
    .project-actions-tab {
        padding: 1;
    }
    
    Tabs {
        Underline {
            & > .underline--bar {
                color: $boost; 
            }
        }
    }
    """

    def compose(self) -> ComposeResult:
        with TabbedContent():
            with TabPane("Download data", id="download-data"):
                yield DownloadData(classes="project-actions-tab")
            with TabPane("User Access", id="user-access"):
                yield UserAccess(classes="project-actions-tab")
