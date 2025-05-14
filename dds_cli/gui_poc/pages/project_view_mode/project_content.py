"""DDS Project Content Widget"""

from textual.app import ComposeResult
from textual.widgets import Static, Tree
from dds_cli.gui_poc.components.dds_container import DDSContainer
from dds_cli.gui_poc.components.dds_tree_view import DDSTreeView, DDSTreeNode

MOCK_PROJECT_CONTENT: DDSTreeNode = DDSTreeNode(
    name="Project Content",
    children=[
        DDSTreeNode(
            name="Project Content 1",
            children=[
                DDSTreeNode(name="Project Content 1.1", children=[]),
                DDSTreeNode(name="Project Content 1.2", children=[]),
                DDSTreeNode(
                    name="Project Content 1.3",
                    children=[
                        DDSTreeNode(name="Project Content 1.3.1", children=[]),
                        DDSTreeNode(name="Project Content 1.3.2", children=[]),
                        DDSTreeNode(name="Project Content 1.3.3", children=[]),
                    ],
                ),
            ],
        ),
        DDSTreeNode(
            name="Project Content 2",
            children=[
                DDSTreeNode(name="Project Content 2.1", children=[]),
                DDSTreeNode(name="Project Content 2.2", children=[]),
                DDSTreeNode(name="Project Content 2.3", children=[]),
            ],
        ),
    ],
)


class ProjectContent(DDSContainer):
    """A widget for the project content."""

    DEFAULT_CSS = """
    ProjectContent {
        border-subtitle-color: $foreground;
    }
    """

    def compose(self) -> ComposeResult:
        yield DDSTreeView(MOCK_PROJECT_CONTENT)

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Change the subtitle on the parent container when a tree node is selected."""
        self.subtitle = event.node.label
