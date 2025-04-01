"""GUI Application for DDS CLI."""

from textual.app import App, ComposeResult
from textual.binding import Binding

from textual.containers import Container, Horizontal
from textual.widgets import ContentSwitcher, Footer, Header, Label, ListItem, ListView
from textual.theme import Theme

from dds_cli.account_manager import AccountManager
from dds_cli.auth import Auth
from dds_cli.gui_poc.data import Data
from dds_cli.gui_poc.home import HomeScreen
from dds_cli.gui_poc.auth import AuthLogin, AuthLogout, AuthStatus
from dds_cli.gui_poc.user import User
from dds_cli.gui_poc.utils import DDSFooter, DDSModal, DDSSidebar


theme = Theme(
    name="custom",
    primary="#3F3F3F",
    secondary="#A6A6A6",
    accent="#A7C947",
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
Input {
    border: solid $primary;
}  
Button {
    padding: 0 2 0 2;
}

    #dds-app-container {
        width: 80%;
        border: solid $primary;
    }

    #dds-app-sidebar {
        width: 20%;
        border: solid $primary;
    }

    """

    ENABLE_COMMAND_PALETTE = False  # True by default

    # Keybindings for the app, placed in the footer.
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("h", "home", "Home", tooltip="Show home screen."),
        Binding("t", "token", "Token", tooltip="Show current token status"),
        Binding("l", "login", "Login", tooltip="Login to DDS."),
        Binding("o", "logout", "Logout", tooltip="Logout from DDS."),
        #Binding("u", "user", "User", tooltip="Show user info."),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True, time_format="%H:%M:%S", icon="")

        with Horizontal(id="dds-app-layout"):
            side =  Container(id="dds-app-sidebar")
            side.border_title = "MENU"
            with side:
                yield ListView(ListItem(Label("Home"), id="home"), ListItem(Label("User"), id="user"), ListItem(Label("Data"), id="data"))
            container = Container(id="dds-app-container")
            container.border_title = "CONTENT"
            with container:
                with ContentSwitcher(initial="home", id="dds-app-content"):
                    with Container(id="home"):
                        yield HomeScreen()          
                    with Container(id="user"):
                        yield User()
                    with Container(id="data"):
                        yield Data()
        yield DDSFooter()

    def action_token(self) -> None:
        """Action to show the token status."""
        self.push_screen(DDSModal(AuthStatus(self.auth), title="Token Status"))

    def action_login(self) -> None:
        """Action to login the user."""
        self.push_screen(DDSModal(AuthLogin(self.token_path), title="Login"))

    def action_logout(self) -> None:
        """Action to logout the user."""
        self.push_screen(DDSModal(AuthLogout(self.auth), title="Logout"))

    def action_user(self) -> None:
        """Action to switch to the user screen."""
        self.query_one(User).user = (
            AccountManager() if self.auth.check() else AccountManager(authenticate=False)
        )  # TODO: possibly not a great solution, works for now
        self.query_one(ContentSwitcher).current = "user"

    def action_home(self) -> None:
        """Action to switch to the home screen."""
        self.query_one(ContentSwitcher).current = "home"

    def on_mount(self) -> None:
        """On mount, register the theme and set it as the active theme."""
        self.register_theme(theme)
        self.theme = "custom"
