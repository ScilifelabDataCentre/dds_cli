"""GUI Application for DDS CLI."""

from textual.app import App, ComposeResult
from textual.binding import Binding

from textual.containers import Container
from textual.widgets import ContentSwitcher, Footer, Header
from textual.theme import Theme

from dds_cli.account_manager import AccountManager
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

    #CSS_PATH = "app.tcss"

    DEFAULT_CSS = """
ModalScreen{
    background: $background 70%;
}

DDSModal {
    align: center middle;
}

#dds-modal{
    width: 50%;
    height: 60%;
    background: $surface;
}

DDSModalFooter {
    align: center middle;
    height: auto;
    padding: 1;
}

DDSModalHeader {
    height: auto;
    align: center middle;
    background: $panel;
}

/* Auth */

AuthStatus {
    align: center middle;
    padding: 1;
}

AuthLogin {
    align: center middle;
}

#auth-login {
    align: center middle;
}

#auth-login > * {
    margin: 1;
}

#auth-login-message {
    text-align: center;
    width: 100%;
    text-wrap: wrap;
}

#login-step {
    align: center middle;
    height: auto;

}

#two-factor-step {
    align: center middle;
    height: auto;

}

#auth-status {
    align: center middle;
}

AuthLogout {
    align: center middle;
}

#auth-logout {
    align: center middle;
    padding: 1;
    height: auto;
}


#auth-logout > * {
    margin: 1;
} 

#auth-logout-message {
    align: center middle;
    height: auto;
}

#auth-logout-buttons {
    align: center middle;
    height: auto;
}

#auth-login {
    align: center middle;
    padding: 1;
    width: 100%;
}

#auth-login > * {
    margin: 1;
    height: auto;
}

/* Home Screen */

#home-screen{
    align: center middle;
}

#title{
    text-style: bold;
}

/* Button */

Button {
    padding: 0 2 0 2;
}

# Button{
#     border: none;
#     height: 3;
#     padding: 0 2 0 2; /* Set padding for centered content without default border*/
# }

# Button:hover{
#     border: none;
# } 

# Button:focus{
#     border: none;
# } 

/* Input */

Input {
    border: solid $primary;
}  

/* Toast */

Toast {
    background: $primary;
}

/* User */ 

#user {
    align: center middle;
    width: 100%; 
}

#user-info {
    align: center middle;
    margin: 1;
}

/* Sidebar */

DDSSidebar {
    dock: left;
    width: 20%;    
    height: 100%; 
    align: center middle;
}

#dds-sidebar {
    align: center middle;
    border: solid $primary;
}

#dds-sidebar-items {
    align: center top;

    height: 80%;
}

#dds-sidebar-items > * {
    margin: 1;
}

#dds-sidebar-help {
    align: center bottom;
    height: 20%;
}

/* File Selector */

FileSelector {
    align: center middle;
    width: 100%;
    height: 100%;
    margin: 1;
}

#file-selector > * {
    margin: 1;
}

#path-input-mode > * {
    margin: 1;
}

#file-selector-switch-container {
    align: center middle;
    width: 100%;
}

InputWithButton {
    layout: horizontal;
    height: auto;
}

#input-with-button-input {
   width: 80%; 
   margin-right: 1;
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

    def action_data(self) -> None:
        """Action to switch to the data screen."""
        self.query_one(ContentSwitcher).current = "data"

    def on_mount(self) -> None:
        """On mount, register the theme and set it as the active theme."""
        self.register_theme(theme)
        self.theme = "custom"
