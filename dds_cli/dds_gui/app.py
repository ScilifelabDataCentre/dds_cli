"""GUI Application for DDS CLI."""

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Header
from textual.theme import Theme

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


class DDSApp(App, DDSStateManager):
    """Textual App for DDS CLI."""

    def __init__(self, token_path: str):
        super().__init__()
        self.token_path = token_path
        self.set_auth_status(self.auth.check())

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
        yield Header(show_clock=True, time_format="%H:%M:%S", icon="")
        yield ProjectView()
        yield DDSFooter()

    def on_mount(self) -> None:
        """On mount, register the theme and set it as the active theme."""
        self.register_theme(theme)
        self.theme = "custom"

    def action_help(self) -> None:
        """Action to show the help screen."""
