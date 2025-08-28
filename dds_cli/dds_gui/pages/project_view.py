"""DDS Project View Page"""

from typing import Any

from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widget import Widget
from textual.widgets import Placeholder
from dds_cli.dds_gui.pages.authentication.authentication import Authentication
from dds_cli.dds_gui.pages.important_information.important_information import ImportantInformation


class ProjectView(Widget):
    """Project view page. Contains the project list, important information,
    authentication menu, project content, project information, and project actions.
    """

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
        height: 40%;
    }
    #important-information {
        height: 35%;
    }
    #auth-menu {
        height: 25%;
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
                yield Placeholder(
                    id="project-list"
                )  # ProjectList(title="Projects", id="project-list")
                yield ImportantInformation(
                    title="Important Information", id="important-information"
                )  # ImportantInformation(title="Important Information", id="important-information")
                yield Authentication(title="Authentication", id="auth-menu")
            with Vertical(id="right-container"):
                with Horizontal(id="top-container"):
                    yield Placeholder(
                        id="project-content"
                    )  # ProjectContent(title="Project Content", id="project-content")
                    yield Placeholder(
                        id="project-information"
                    )  # ProjectInformation(title="Project Information", id="project-information")
                with Horizontal(id="bottom-container"):
                    yield Placeholder(
                        id="project-actions"
                    )  # ProjectActions(title="Project Actions", id="project-actions")
