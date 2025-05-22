"""DDS Authentication Page"""

from typing import Any
from textual.app import ComposeResult
from textual.events import Click
from textual.widgets import ContentSwitcher, Label

from dds_cli.dds_gui.components.dds_container import DDSContainer, DDSSpacedContainer
from dds_cli.dds_gui.components.dds_button import DDSSkinnyButton
from dds_cli.dds_gui.pages.authentication.modals.login_modal import LoginModal
from dds_cli.dds_gui.pages.authentication.modals.logout_modal import LogoutModal
from dds_cli.dds_gui.pages.authentication.modals.reauthenticate_modal import ReAuthenticateModal


class Authentication(DDSContainer):
    """An auth menu widget for the GUI."""

    def __init__(self, title: str, *args: Any, **kwargs: Any) -> None:
        super().__init__(title=title, *args, **kwargs)

    DEFAULT_CSS = """
    .auth-status { 
        width: 100%;
        text-align: center;
       }    
    """

    def compose(self) -> ComposeResult:
        with ContentSwitcher(id="auth-status-switcher"):
            with DDSSpacedContainer(id="auth-status-ok-container"):
                yield Label("✅ Authenticated ✅", classes="auth-status")
                yield DDSSkinnyButton("Logout", id="logout")
                yield DDSSkinnyButton("Re-authenticate", id="re-authenticate")
            with DDSSpacedContainer(id="auth-status-invalid-container"):
                yield Label("❌ Not authenticated ❌", classes="auth-status")
                yield DDSSkinnyButton("Login", id="login")

    def on_mount(self) -> None:
        """On mount, set initial state."""
        self.watch_auth_status(self.app.auth_status)

    def watch_auth_status(self, auth_status: bool) -> None:
        """Watch the auth status and change content accordingly."""
        if auth_status:
            self.query_one("#auth-status-switcher").current = "auth-status-ok-container"
        else:
            self.query_one("#auth-status-switcher").current = "auth-status-invalid-container"

    def on_button_pressed(self, event: Click) -> None:
        """Handle button presses."""
        if event.button.id == "login":
            self.app.push_screen(LoginModal())
        elif event.button.id == "logout":
            self.app.push_screen(LogoutModal())
        elif event.button.id == "re-authenticate":
            self.app.push_screen(ReAuthenticateModal())
