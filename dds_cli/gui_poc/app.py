"""GUI Application for DDS CLI."""

from textual.app import App, ComposeResult
from textual.binding import Binding

from textual.widgets import Header
from textual.theme import Theme

from dds_cli.auth import Auth
from dds_cli.gui_poc.pages.dds_base_page import DDSBasePage
from dds_cli.gui_poc.utils import DDSFooter


theme = Theme(
    name="custom",
    primary="#3F3F3F",
    secondary="#4C979F",
    accent="#A7C947",
    foreground="#FFFFFF",
    panel="#045C64",
    boost="#12F0E1",
    warning="#F57C00",
    error="#D32F2F",
    success="#388E3C",
    dark=True,
    variables={
        "block-hover-background": "#43858B",
        "primary-darken-2": "#323232",
    },
)


class DDSApp(App):
    """Textual App for DDS CLI."""

    def __init__(self, token_path: str):
        super().__init__()
        self.token_path = token_path
        self.auth = Auth(authenticate=False, token_path=token_path)

    DEFAULT_CSS = """
    Toast {
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
        yield DDSBasePage(self.token_path)
        yield DDSFooter()

    def on_mount(self) -> None:
        """On mount, register the theme and set it as the active theme."""
        self.register_theme(theme)
        self.theme = "custom"

    def action_help(self) -> None:
        """Action to show the help screen."""
