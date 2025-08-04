"""DDS Authentication Form"""

from typing import Any, Callable

from textual.app import ComposeResult, events
from textual.containers import Container
from textual.reactive import reactive

import dds_cli
from dds_cli.dds_gui.components.dds_form import DDSForm
from dds_cli.dds_gui.components.dds_input import DDSInput
from dds_cli.dds_gui.components.dds_button import DDSButton
from dds_cli.auth import Auth
import dds_cli.exceptions


class AuthenticationForm(Container):
    """A widget for the authentication form.
    Comment out becuse all auth functionaity for the gui is disabled for now.
    """

    def __init__(self, close_modal: Callable, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.auth = Auth(authenticate=False, token_path=self.app.token_path)
        self.close_modal = close_modal

    partial_auth_token: reactive[str] = reactive(None)
    secondfactor_method: reactive[str] = reactive(None)

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
                self.query_one("#dds-auth-form-container").mount(
                    TwoFactorFormFields(id="dds-2fa-form")
                )
        if event.button.id == "login":
            self.confirm_2factor_code()

    def authenticate_user_credentials(self) -> None:
        """Authenticate the user credentials."""
        username = self.query_one("#username").value
        password = self.query_one("#password").value

        try:
            self.partial_auth_token, self.secondfactor_method = self.auth.login(username, password)
            self.notify("Two factor code sent to email.")
        except (
            dds_cli.exceptions.AuthenticationError,
            dds_cli.exceptions.ApiRequestError,
        ) as error:
            self.notify(f"Error: {error}", severity="error")
            self.auth = None

    def confirm_2factor_code(self) -> None:
        """Confirm the 2FA code."""
        code = self.query_one("#code").value

        try:
            self.auth.confirm_twofactor(
                partial_auth_token=self.partial_auth_token,
                secondfactor_method=self.secondfactor_method,
                twofactor_code=code,
            )
            self.notify("Successfully authenticated.")
            self.app.set_auth_status(True)
        except dds_cli.exceptions.AuthenticationError as error:
            self.notify(f"Error: {error}", severity="error", timeout=10)
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
            yield DDSButton("Login", id="send-2fa-code", variant="primary")


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
            yield DDSButton("Authenticate", id="login", variant="primary")
