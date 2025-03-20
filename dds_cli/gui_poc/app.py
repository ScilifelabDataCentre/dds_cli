from textual.app import App, ComposeResult
from textual.binding import Binding, BindingType

from textual.containers import Container
from textual.widgets import ContentSwitcher, Footer, Header
from textual.theme import Theme

from dds_cli.auth import Auth
from dds_cli.gui_poc.data import Data
from dds_cli.gui_poc.home import HomeScreen
from dds_cli.gui_poc.auth import AuthLogin, AuthLogout, AuthStatus
from dds_cli.gui_poc.user import User
from dds_cli.gui_poc.utils import DDSModal


theme = Theme(
    name="custom",
    primary="#3F3F3F",
    secondary="#A6A6A6",
    accent = "#A7C947",
    foreground="#FFFFFF",
    panel="#045C64",
    boost="#39ef6d",
    warning="#F57C00",
    error="#D32F2F",
    success="#388E3C",
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
        Binding("q", "quit", "Quit"), 
        Binding("h", "home", "Home", tooltip="Show home screen."),
        Binding("t", "token", "Token", tooltip="Show current token status"), 
        Binding("l", "login", "Login", tooltip="Login to DDS."),
        Binding("o", "logout", "Logout", tooltip="Logout from DDS."),
        Binding("u", "user", "User", tooltip="Show user info."),
        Binding("d", "data", "Data", tooltip="Show data info."),
    ]
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True, time_format="%H:%M:%S", icon="")
        with ContentSwitcher(initial="home"):
            with Container(id="home"):
                yield HomeScreen()
            with Container(id="user"):
                yield User()
            with Container(id="data"):
                yield Data()
        yield Footer()

    def action_token(self) -> None:
        self.push_screen(DDSModal(AuthStatus(self.auth), title="Token Status"))
    
    def action_login(self) -> None:
        self.push_screen(DDSModal(AuthLogin(self.token_path), title="Login"))

    def action_logout(self) -> None:
        self.push_screen(DDSModal(AuthLogout(self.auth), title="Logout"))

    def action_user(self) -> None:
        self.query_one(ContentSwitcher).current = "user"

    def action_home(self) -> None:
        self.query_one(ContentSwitcher).current = "home"

    def action_data(self) -> None:
        self.query_one(ContentSwitcher).current = "data"

    def on_mount(self) -> None:
        self.register_theme(theme)
        self.theme = "custom"
