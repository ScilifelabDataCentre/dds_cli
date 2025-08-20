"""DDS Project Content Widget"""

from textual.app import ComposeResult
from textual.widgets import Label, LoadingIndicator, Tree
from textual.reactive import reactive

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

    # Local reactive attributes that mirror app state and trigger recomposition
    # We should not need to use these reactive attributes, but it's not working without them.
    project_content: reactive[ProjectContentData | None] = reactive(None, recompose=True)
    selected_project_id: reactive[str | None] = reactive(None, recompose=True)
    is_loading: reactive[bool] = reactive(False, recompose=True)

    def compose(self) -> ComposeResult:
        """Compose the widget based on current state."""
        if self.project_content:
            # Show tree view when we have content
            yield TreeView(self.project_content)
        elif self.is_loading:
            # Show loading when project selected but no content yet
            yield LoadingIndicator()
        elif self.selected_project_id and not self.is_loading and not self.project_content:
            # Show no data message when project selected but no content found
            yield Label(f"No data found for project {self.selected_project_id}")
        else:
            # Show default message when no project selected
            yield Label("No project selected")

    def on_mount(self) -> None:
        """On mount, sync initial state and set up watchers."""
        # Initialize local reactive attributes with current app state
        self.is_loading = self.app.is_loading
        self.project_content = self.app.project_content
        self.selected_project_id = self.app.selected_project_id

        # Set up watchers to keep local state in sync with app state
        self.watch(self.app, "is_loading", self.watch_is_loading)
        self.watch(self.app, "project_content", self.watch_project_content)
        self.watch(self.app, "selected_project_id", self.watch_selected_project_id)

    def watch_is_loading(self, is_loading: bool) -> None:
        """Watch the app's is_loading state and sync to local reactive attribute."""
        self.is_loading = is_loading

    def watch_project_content(self, project_content: ProjectContentData | None) -> None:
        """Watch the app's project_content state and sync to local reactive attribute."""
        self.project_content = project_content

    def watch_selected_project_id(self, selected_project_id: str | None) -> None:
        """Watch the app's selected_project_id state and sync to local reactive attribute."""
        self.selected_project_id = selected_project_id

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Change the subtitle on the parent container when a tree node is selected."""
        self.subtitle = event.node.label
