"""Auth widgets."""

from textual.app import ComposeResult
from textual.containers import Container, Vertical, VerticalScroll
from textual.widgets import Button, Label, Input
from textual import events
from textual.widget import Widget

from dds_cli.auth import Auth


class AuthStatus(Widget):
    """Authentication status widget."""

    DEFAULT_CSS = """
    AuthStatus {
    align: center middle;
    padding: 1;
}
#auth-status {
    align: center middle;
}
    """

    def __init__(self, auth: Auth):
        super().__init__()
        self.auth = auth

    def compose(self) -> ComposeResult:
        with Container(id="auth-status"):
            yield Label(self.get_status())

    def get_status(self) -> str:
        """Return the authenticatin status of the user."""
        return self.auth.check() or "Not authenticated"


class LoginStep(Widget):
    """Login step of the login widget."""

    DEFAULT_CSS = """
    #login-step {
    align: center middle;
    height: auto;

}"""

    def __init__(self, auth: Auth, token_path: str):
        super().__init__()
        self.auth = auth
        self.token_path = token_path

    def compose(self) -> ComposeResult:
        with Container(id="login-step"):
            yield Input(placeholder="Username", id="username")
            yield Input(placeholder="Password", id="password", password=True)
            yield Button("Login", id="login", variant="primary")


class TwoFactorStep(Widget):
    """Two factor step of the login widget."""

    DEFAULT_CSS = """
    #two-factor-step {
    align: center middle;
    height: auto;

}"""

    def __init__(self, auth: Auth):
        super().__init__()
        self.auth = auth

    def compose(self) -> ComposeResult:
        with Container(id="two-factor-step"):
            yield Input(placeholder="2FA Code", id="code")
            yield Button("Complete Login", id="complete-login", variant="primary")


class AuthLogin(Widget):
    """Login widget."""

    DEFAULT_CSS = """ 
    AuthLogin {
    align: center middle;
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

#auth-login-message {
    text-align: center;
    width: 100%;
    text-wrap: wrap;
}

    """

    def __init__(self, token_path: str):
        super().__init__()
        self.auth = None
        self.token_path = token_path

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="auth-login"):
            yield Label(
                "Authenticate yourself towards SciLifeLab Data Delivery System.",
                id="auth-login-message",
            )
            yield LoginStep(self.auth, self.token_path)

    def on_button_pressed(self, event: events.Click) -> None:
        """Handles button presses."""
        if event.button.id == "login":
            self.authenticate_user_credentials()

            if (
                self.auth
            ):  # If authentication was successful, remove the login step and mount the 2factor step.
                self.query_one("#login-step").remove()
                self.query_one("#auth-login").mount(TwoFactorStep(self.auth))
                self.notify("Two factor code sent to email.")

        if event.button.id == "complete-login":
            self.confirm_2factor_code()

    def authenticate_user_credentials(self) -> None:
        """Authenticates the user credentials. Sets the auth object if successful."""
        username = self.query_one("#username").value
        password = self.query_one("#password").value
        self.auth = Auth(
            authenticate=False,
            authenticate_gui=True,
            token_path=self.token_path,
            username_gui=username,
            password_gui=password,
        )

    def confirm_2factor_code(self) -> None:
        """Confirms the 2factor code. Removes the 2factor step and notifies the user."""
        code = self.query_one("#code").value

        self.auth.do_2factor(code)
        self.query_one("#complete-login").remove()
        self.notify("Successfully logged in.")


class AuthLogout(Widget):
    """Logout widget."""

    DEFAULT_CSS = """
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
    """

    def __init__(self, auth: Auth):
        super().__init__()
        self.auth = auth

    def compose(self) -> ComposeResult:
        with Vertical(id="auth-logout"):
            yield Container(
                Label("Are you sure you want to logout? If not, press close."),
                id="auth-logout-message",
            )
            with Container(id="auth-logout-buttons"):
                yield Button("Logout", variant="warning", id="logout")

    def on_button_pressed(self, event: events.Click) -> None:
        """Handles button presses."""
        if event.button.id == "logout":
            logout = self.auth.logout()
            self.query_one("#auth-logout-buttons").disabled = True
            if logout:
                self.notify("Successfully logged out.")
            else:
                self.notify("Already logged out.")
