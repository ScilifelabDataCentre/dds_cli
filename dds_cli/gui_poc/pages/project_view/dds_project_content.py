"""DDS Project Content Widget"""

from typing import Any
from textual.app import ComposeResult
from textual.widgets import Label, Switch, Tree
from dds_cli.gui_poc.components.dds_container import DDSContainer
from dds_cli.gui_poc.components.dds_tree_view import DDSTreeView, DDSTreeNode

MOCK_PROJECT_CONTENT: DDSTreeNode = DDSTreeNode(
    name="Project Content",
    children=[
        DDSTreeNode(name="Project Content 1", children=[
            DDSTreeNode(name="Project Content 1.1", children=[]),
            DDSTreeNode(name="Project Content 1.2", children=[]),
            DDSTreeNode(name="Project Content 1.3", children=[
                DDSTreeNode(name="Project Content 1.3.1", children=[]),
                DDSTreeNode(name="Project Content 1.3.2", children=[]),
                DDSTreeNode(name="Project Content 1.3.3", children=[]),
            ]),
        ]),
        DDSTreeNode(name="Project Content 2", children=[
            DDSTreeNode(name="Project Content 2.1", children=[]),
            DDSTreeNode(name="Project Content 2.2", children=[]),
            DDSTreeNode(name="Project Content 2.3", children=[]),
        ]),
    ]
)

class DDSProjectContent(DDSContainer):
    """A widget for the project content."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

    def compose(self) -> ComposeResult:
        yield DDSTreeView(MOCK_PROJECT_CONTENT)
