from textual.app import App, ComposeResult
from textual.binding import Binding

from textual.widgets import Footer, Header
from textual.theme import Theme

from dds_cli.auth import Auth
from dds_cli.gui_poc.home import HomeScreen
from dds_cli.gui_poc.auth import AuthLogin, AuthLogout, AuthStatus
from dds_cli.gui_poc.utils import DDSModal


theme = Theme(
    name="custom",
    primary="#3F3F3F",
    accent = "#A7C947",
    foreground="#FFFFFF",
    panel="#045C64",
    boost="#FFFFFF",
    warning="#FF6600",
    dark=True,
    variables={
        "block-hover-background": "#43858B",
        "primary-darken-2": "#323232",
        #"button-focus-text-style": "underline",
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
        Binding("q", "quit", "Quit"), 
        ("a", "authenticate", "Session Status"), 
        ("l", "login", "Login"),
        ("o", "logout", "Logout"),
    ]
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True, time_format="%H:%M:%S", icon="")
        yield HomeScreen()
        yield Footer()

    def action_authenticate(self) -> None:
        self.push_screen(DDSModal(AuthStatus(self.auth)))
    
    def action_login(self) -> None:
        self.push_screen(DDSModal(AuthLogin(self.token_path)))

    def action_logout(self) -> None:
        self.push_screen(DDSModal(AuthLogout(self.auth)))
    
    def on_mount(self) -> None:
        self.register_theme(theme)
        self.theme = "custom"
