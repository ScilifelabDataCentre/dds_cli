"""GUI Application for DDS CLI."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.theme import Theme
from textual.widgets import Header
from textual.widgets._header import HeaderTitle
from textual.css.query import NoMatches

from dds_cli.dds_gui.components.dds_footer import DDSFooter
from dds_cli.dds_gui.dds_state_manager import DDSStateManager
from dds_cli.dds_gui.pages.project_view import ProjectView

theme = Theme(
    name="custom",
    primary="#666666",  # "#3F3F3F",
    secondary="#4C979F",
    # secondary="#12F0E1",
    accent="#A7C947",
    foreground="#FFFFFF",
    panel="#045C64",
    boost="#12F0E1",
    warning="#F57C00",
    error="#D32F2F",
    success="#388E3C",
    dark=True,
    variables={
        # "block-hover-background": "#43858B",
        "block-hover-background": "#616060",
        # "block-hover-foreground": "green",
        # "primary-darken-2": "#323232",
        # "block-cursor-blurred-background": "red",
        # "block-cursor-background": "#12F0E1", #Tab color
    },
)


class SafeHeader(Header):
    """Header widget that handles HeaderTitle access gracefully in test environments."""
    
    def query_one(self, selector, expect_type=None):
        """Override query_one to handle HeaderTitle access gracefully."""
        try:
            return super().query_one(selector, expect_type)
        except NoMatches as e:
            # If we're looking for HeaderTitle and it's not found, return a mock
            if selector == HeaderTitle:
                # Return a mock HeaderTitle widget that won't cause issues
                from textual.widgets import Static
                mock_title = Static("")
                mock_title.update = lambda x: None  # Mock update method
                return mock_title
            raise e


class DDSApp(DDSStateManager):  ### Moved Textual App class to State Manager to access notifications
    """Textual App for DDS CLI."""

    def __init__(self, token_path: str):
        super().__init__()
        self.token_path = token_path
        self._mounted = False  # Initialize _mounted attribute
        # Check auth status immediately so UI shows correct state
        auth_status = self.auth.check() is not None
        self.set_auth_status(auth_status)

        # If authenticated, set loading state for projects
        if auth_status:
            self.projects_loading = True

    # TODO: add scrollbar styling here?
    DEFAULT_CSS = """
    Toast.-error {
        background: $primary;
    }

    """

    ENABLE_COMMAND_PALETTE = False  # True by default

    # Keybindings for the app, placed in the footer.
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("h", "help", "Help"),
    ]

    def compose(self) -> ComposeResult:
        yield SafeHeader(icon="", show_clock=True, time_format="%H:%M:%S")
        yield ProjectView()
        yield DDSFooter()

    def on_mount(self) -> None:
        """On mount, register the theme and set it as the active theme."""
        self.register_theme(theme)
        self.theme = "custom"
        # Mark that the GUI is mounted - prevents auth watcher from fetching projects during initialization
        self._mounted = True  # pylint: disable=attribute-defined-outside-init
        # Now that the GUI is mounted, fetch projects if authenticated
        self.call_after_refresh(self._fetch_projects_if_authenticated)

    def _fetch_projects_if_authenticated(self) -> None:
        """Fetch projects if user is authenticated, after GUI is ready."""
        if self.auth_status:
            self.fetch_projects_async()

    def action_help(self) -> None:
        """Action to show the help screen."""
