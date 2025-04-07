from typing import Any

from textual import events
from textual.app import ComposeResult
from textual.containers import Container
from textual.widget import Widget
from textual.widgets import Label

from dds_cli.auth import Auth
from dds_cli.gui_poc.components.dds_button import DDSButton, DDSFormButton
from dds_cli.gui_poc.components.dds_form import DDSForm
from dds_cli.gui_poc.components.dds_input import DDSInput
from dds_cli.gui_poc.components.dds_modal import DDSModal
from dds_cli.gui_poc.components.dds_text_item import DDSTextSubtitle, DDSTextTitle
from dds_cli.gui_poc.components.dds_container import DDSContainer

class DDSLoginPage(DDSContainer):
    """A widget for the Login page."""
    def __init__(self, token_path: str, *args: Any, **kwargs: Any):
        super().__init__(title="Login", *args, **kwargs)
        self.token_path = token_path
    
    def compose(self) -> ComposeResult:
        yield DDSTextTitle("Login")
        yield DDSTextSubtitle("Please enter your credentials to authenticate with the DDS.")
        yield DDSAuthForm(self.token_path)


class DDSReAuthenticatePage(DDSContainer):
    """A widget for the Re-authenticate page."""
    def __init__(self, token_path: str, *args: Any, **kwargs: Any):
        super().__init__(title="Re-authenticate", *args, **kwargs)  
        self.token_path = token_path

    def compose(self) -> ComposeResult:
        yield DDSTextTitle("Re-authenticate")
        yield DDSTextSubtitle("Please enter your credentials to re-authenticate with the DDS.")
        yield DDSAuthForm(self.token_path)


class DDSAuthForm(Container):
    """A widget for the authentication form."""
    def __init__(self, token_path: str, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.auth = None
        self.token_path = token_path

    def compose(self) -> ComposeResult:
        with Container(id="dds-auth-form"):
            yield DDSLoginFormFields()
        with Container(id="dds-2fa-form"):
            yield DDS2FAFormFields()


    def on_mount(self) -> None:
        """On mount, set the form to the login form."""
        self.query_one("#dds-auth-form").visible = True
        self.query_one("#dds-2fa-form").visible = False
    
    
    def on_button_pressed(self, event: events.Click) -> None:
        """Handle button presses."""
        if event.button.id == "send-2fa-code":
            self.authenticate_user_credentials()
            if self.auth:
                self.query_one("#dds-auth-form").visible = False
                self.query_one("#dds-2fa-form").visible = True
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
        self.auth.do_2factor(code)
        self.notify("Successfully logged in.")

    
class DDSLoginFormFields(DDSForm):
    """A widget for the authentication form fields."""
    def compose(self) -> ComposeResult:
        yield DDSInput(placeholder="Username", id="username")
        yield DDSInput(placeholder="Password", id="password", password=True)
        yield DDSFormButton("Send 2FA code", id="send-2fa-code")


class DDS2FAFormFields(DDSForm):
    """A widget for the 2FA form fields."""
    def compose(self) -> ComposeResult:
        yield DDSInput(placeholder="2FA code", id="code")
        yield DDSFormButton("Login", id="login")


class DDSLogout(DDSModal):
    """A widget for the logout modal."""

    def __init__(self, token_path: str, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.token_path = token_path

    def compose(self) -> ComposeResult:
        yield Label("Are you sure you want to logout?")
        yield DDSButton("Logout", id="logout", variant="warning")
