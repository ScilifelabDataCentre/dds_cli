from rich.segment import Segment
from rich.style import Style
from rich_pixels import Pixels
from textual import events
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Grid, Vertical, VerticalScroll
from textual.screen import ModalScreen, Screen
from textual.widget import Widget
from textual.widgets import Button, Footer, Header, Input, Label, Static
from textual.theme import Theme

from dds_cli.auth import Auth
from dds_cli.gui_poc.home import HomeScreen
from dds_cli.gui_poc.auth import AuthModal


theme = Theme(
    name="custom",
    primary="#3F3F3F",
    accent = "#A7C947",
    foreground="#FFFFFF",
    panel="#045C64",
    boost="#FFFFFF",
    warning="#FF0000",
    dark=True,
    variables={
        "block-hover-background": "#43858B",
        "primary-darken-2": "#323232",
    },
)   


class App(App):
    def __init__(self, token_path: str):
        super().__init__()
        self.token_path = token_path
        self.auth = Auth(authenticate=False, token_path=token_path)

    CSS_PATH = "app.tcss"

    ENABLE_COMMAND_PALETTE = False

    BINDINGS = [
        Binding("q", "quit", "Quit"), ("a", "authenticate", "Authenticate")
    ]
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True, time_format="%H:%M:%S")
        yield HomeScreen()
        yield Footer()

    def action_authenticate(self) -> None:
        self.push_screen(AuthModal(self.auth, self.token_path))

    def on_mount(self) -> None:
        self.register_theme(theme)
        self.theme = "custom"
