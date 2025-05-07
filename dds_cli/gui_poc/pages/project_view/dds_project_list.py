"""DDS Project List Widget"""

from typing import Any
from textual.app import ComposeResult
from textual.widgets import Label, Select
from dds_cli.gui_poc.components.dds_button import DDSButton
from dds_cli.gui_poc.components.dds_container import DDSContainer, DDSSpacedContainer
from dds_cli.gui_poc.components.dds_data_table import DDSDataTable
from dds_cli.gui_poc.components.dds_select import DDSSelect
from dds_cli.gui_poc.components.dds_text_item import DDSTextItem


MOCK_PROJECTS = [
    ("Project 1"),
    ("Project 2"),
    ("Project 3"),
    ("Project 4"),
    ("Project 5"),
]

class DDSProjectList(DDSContainer):
    """A widget for the project list."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

    def compose(self) -> ComposeResult:
        with DDSSpacedContainer():
            yield DDSTextItem("Select a project to view the project content, information, invite users, and upload and download data.")
            yield DDSSelect(title="Select a project", data=MOCK_PROJECTS)
            yield DDSButton("View Project", id="view-project")
        #yield DDSDataTable(header=["Project Name"], data=MOCK_PROJECTS)


