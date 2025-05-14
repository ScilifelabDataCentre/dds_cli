
from typing import Any
from textual.app import ComposeResult
from textual.widgets import ContentSwitcher, Label
from dds_cli.gui_poc.components.dds_container import DDSContainer, DDSSpacedContainer
from dds_cli.gui_poc.components.dds_button import DDSSkinnyButton

class Authentication(DDSContainer):
    """An auth menu widget for the GUI."""

    def __init__(self, title: str, *args: Any, **kwargs: Any) -> None:
        super().__init__(title=title, *args, **kwargs)

    DEFAULT_CSS = """
    #auth-status-ok { 
        width: 100%;
        text-align: center;
       }    

    #auth-status-invalid { 
        width: 100%;
        text-align: center;
       }    
    """

    def compose(self) -> ComposeResult:
        with ContentSwitcher(id="auth-status-switcher"):
            with DDSSpacedContainer(id="auth-status-ok-container"):
                    yield Label("✅ Authenticated ✅", id="auth-status-ok")
                    yield DDSSkinnyButton("Logout", id="logout")
                    yield DDSSkinnyButton("Re-authenticate", id="re-authenticate")
            with DDSSpacedContainer(id="auth-status-invalid-container"):
                yield Label("❌ Not authenticated ❌", id="auth-status-invalid")
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
