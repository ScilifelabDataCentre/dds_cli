"""DDS Project Content Widget"""

from textual.app import ComposeResult
from textual.widgets import Label, Tree

from dds_cli.dds_gui.components.dds_container import DDSContainer
from dds_cli.dds_gui.pages.project_content.components.tree_view import TreeView
from dds_cli.dds_gui.models.project import ProjectContentData


class ProjectContent(DDSContainer):
    """A widget for the project content."""

    DEFAULT_CSS = """
    ProjectContent {
        border-subtitle-color: $foreground;
    }
    """

    def compose(self) -> ComposeResult:
        if self.app.project_content:
            yield TreeView(self.app.project_content)  # .set_loading(False)
        elif self.app.selected_project_id:
            yield Label(f"No data found for project {self.app.selected_project_id}")
        else:
            yield Label("No project selected")

    def watch_project_content(self, project_content: ProjectContentData) -> None:
        """Watch the project_content state and update the tree view when the selected project changes."""
        #self.mount(TreeView(project_content))

    # def watch_selected_project_id(self, selected_project_id: str) -> None:
    #     """Watch the selected project id."""
    #     self.notify(f"Selected project id changed to {selected_project_id}", severity="information")
    #     self.mount(Label(f"No data found for project {selected_project_id}"))

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Change the subtitle on the parent container when a tree node is selected."""
        self.subtitle = event.node.label
