"""DDS Project List Widget"""

from textual.app import ComposeResult
from dds_cli.gui_poc.components.dds_button import DDSButton
from dds_cli.gui_poc.components.dds_container import DDSContainer, DDSSpacedContainer
from dds_cli.gui_poc.components.dds_select import DDSSelect
from dds_cli.gui_poc.components.dds_text_item import DDSTextItem


MOCK_PROJECTS = [
    ("Project 1"),
    ("Project 2"),
    ("Project 3"),
    ("Project 4"),
    ("Project 5"),
]


class ProjectList(DDSContainer):
    """A widget for the project list selection."""

    def compose(self) -> ComposeResult:
        with DDSSpacedContainer():
            yield DDSTextItem(
                "Select a project to view the project content, information, invite users, and upload and download data."
            )
            yield DDSSelect(title="Select a project", data=MOCK_PROJECTS)
            yield DDSButton("View Project", id="view-project")
