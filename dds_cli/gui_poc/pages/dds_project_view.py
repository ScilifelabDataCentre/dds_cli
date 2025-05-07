from typing import Any

from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widget import Widget
from dds_cli.gui_poc.pages.dds_base_page import DDSAuthMenu
from dds_cli.gui_poc.pages.project_view.dds_project_list import DDSProjectList
from dds_cli.gui_poc.pages.project_view.dds_project_content import DDSProjectContent
from dds_cli.gui_poc.pages.project_view.dds_project_information import DDSProjectInformation
from dds_cli.gui_poc.pages.project_view.dds_project_actions import DDSProjectActions


class DDSProjectView(Widget):
    """A widget for the project view."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)


    DEFAULT_CSS = """
    #left-container {
        width: 25%;
    }
    #right-container {
        width: 75%;
    }
    #project-list {
        height: 70%;
    }
    #auth-menu {
        height: 30%;
    }   
    #top-container {
        height: 50%;
    }
    #bottom-container {
        height: 50%;
    }   
    #project-content {
        width: 60%;
    }
    #project-information {
        width: 40%;
    }
    
    """

    def compose(self) -> ComposeResult:
        with Horizontal():
            with Vertical(id="left-container"):
                yield DDSProjectList(title="Projects", id="project-list")
                yield DDSAuthMenu(title="Authentication", id="auth-menu")
            with Vertical(id="right-container"):
                with Horizontal(id="top-container"):
                    yield DDSProjectContent(title="Project Content", id="project-content")
                    yield DDSProjectInformation(title="Project Information", id="project-information")
                with Horizontal(id="bottom-container"):
                    yield DDSProjectActions(title="Project Actions", id="project-actions")
        