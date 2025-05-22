"""DDS Project Content Widget"""

from textual.app import ComposeResult
from textual.widgets import Label, Tree

from dds_cli.dds_gui.components.dds_container import DDSContainer
from dds_cli.dds_gui.components.dds_tree_view import DDSTreeView, DDSTreeNode


class ProjectContent(DDSContainer):
    """A widget for the project content."""

    DEFAULT_CSS = """
    ProjectContent {
        border-subtitle-color: $foreground;
    }
    """

    def compose(self) -> ComposeResult:
        if self.app.project_content:
            yield DDSTreeView(self.app.project_content)  # .set_loading(False)
        else:
            yield Label("No project selected")

    def watch_project_content(self, project_content: DDSTreeNode) -> None:
        """Watch the project_content state and update the tree view when the selected project changes."""
        self.mount(DDSTreeView(project_content))

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Change the subtitle on the parent container when a tree node is selected."""
        self.subtitle = event.node.label
