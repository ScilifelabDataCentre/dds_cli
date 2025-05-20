from typing import Any, Callable
from textual import events
from textual.app import ComposeResult
from textual.containers import Container
from dds_cli.auth import Auth
from dds_cli.gui_poc.components.dds_form import DDSForm
from dds_cli.gui_poc.components.dds_input import DDSInput
from dds_cli.gui_poc.components.dds_button import DDSButton, DDSFormButton


class AuthenticationForm(Container):
    """A widget for the authentication form."""

    def __init__(self, token_path: str, close_modal: Callable, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.auth = None
        self.token_path = token_path
        self.close_modal = close_modal

    DEFAULT_CSS = """
    #dds-auth-form {
        height: 100%;
    }
    #dds-2fa-form {
        height: 100%;
    }
    """

    def compose(self) -> ComposeResult:
        with Container(id="dds-auth-form-container"):
            yield LoginFormFields(id="dds-auth-form")

    def on_mount(self) -> None:
        """On mount, set the form to the login form."""

    def on_button_pressed(self, event: events.Click) -> None:
        """Handle button presses."""
        if event.button.id == "send-2fa-code":
            self.authenticate_user_credentials()
            if self.auth:
                self.query_one("#dds-auth-form").remove()
                self.query_one("#dds-auth-form-container").mount(TwoFactorFormFields(id="dds-2fa-form"))
        if event.button.id == "login":
            self.confirm_2factor_code()

    def authenticate_user_credentials(self) -> None:
        """Authenticate the user credentials."""
        username = self.query_one("#username").value
        password = self.query_one("#password").value

        try:
            self.auth = Auth(
                authenticate=False,
                authenticate_gui=True,
                token_path=self.token_path,
                username_gui=username,
                password_gui=password,
            )
            self.notify("Two factor code sent to email.")
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")
            self.auth = None

    def confirm_2factor_code(self) -> None:
        """Confirm the 2FA code."""
        code = self.query_one("#code").value
        try:
            self.auth.do_2factor(code)
            self.notify("Successfully logged in.")
            self.app.compute_auth_status()
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")
        self.close_modal()    


class LoginFormFields(DDSForm):
    """A widget for the authentication form fields."""

    DEFAULT_CSS = """
    #dds-auth-form-button {
        width: 100%;
        align: right middle;
    }
    """

    def compose(self) -> ComposeResult:
        yield DDSInput(placeholder="Username", id="username")
        yield DDSInput(placeholder="Password", id="password", password=True)
        with Container(id="dds-auth-form-button"):
            yield DDSButton("Send 2FA code", id="send-2fa-code", variant="primary")


class TwoFactorFormFields(DDSForm):
    """A widget for the 2FA form fields."""

    DEFAULT_CSS = """
    #dds-2fa-form-button {
        width: 100%;
        align: right middle;
    }
    """

    def compose(self) -> ComposeResult:
        yield DDSInput(placeholder="2FA code", id="code")
        with Container(id="dds-2fa-form-button"):
            yield DDSButton("Login", id="login", variant="primary")
