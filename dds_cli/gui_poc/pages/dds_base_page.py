"""DDS Base Page Widget"""

from typing import Any
from textual import events
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widget import Widget
from textual.widgets import Button, ContentSwitcher, Label

from dds_cli.auth import Auth
from dds_cli.gui_poc.components.dds_button import DDSButton, DDSSkinnyButton
from dds_cli.gui_poc.components.dds_container import DDSContainer, DDSSpacedContainer
from dds_cli.gui_poc.pages.dds_auth import DDSLoginPage, DDSLogout, DDSReAuthenticatePage
from dds_cli.gui_poc.pages.dds_home import DDSHomePage


class DDSBasePage(Widget):
    """A base page widget for the GUI. Handles the menu and content switching."""

    def __init__(self, token_path: str) -> None:
        super().__init__()
        self.token_path = token_path

    DEFAULT_CSS = """
    DDSSidebar {
        width: 20%;
    }
    """

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield DDSSidebar(self.token_path)
            with ContentSwitcher(initial="home", id="dds-content-switcher"):
                yield DDSHomePage(id="home")
                yield DDSLoginPage(self.token_path, id="login")
                yield DDSReAuthenticatePage(self.token_path, id="re-authenticate")

    def on_button_pressed(self, event: events.Click) -> None:
        """Handle button presses."""
        if event.button.id == "home":
            self.query_one(ContentSwitcher).current = "home"
        elif event.button.id == "login":
            self.query_one(ContentSwitcher).current = "login"
        elif event.button.id == "re-authenticate":
            self.query_one(ContentSwitcher).current = "re-authenticate"
        elif event.button.id == "logout":
            self.app.push_screen(DDSLogout(self.token_path))


class DDSSidebar(Widget):
    """A sidebar widget for the GUI."""

    def __init__(self, token_path: str) -> None:
        super().__init__()
        self.token_path = token_path

    DEFAULT_CSS = """
    DDSMenu {
        height: 70%;
    }

    DDSAuthMenu {
        height: 30%;
    } """

    def compose(self) -> ComposeResult:
        yield DDSMenu("Menu")
        yield DDSAuthMenu("Auth")


class DDSMenu(DDSContainer):
    """A menu widget for the GUI."""

    def __init__(self, title: str, *args: Any, **kwargs: Any) -> None:
        super().__init__(title=title, *args, **kwargs)

    DEFAULT_CSS = """
    """

    def compose(self) -> ComposeResult:
        with DDSSpacedContainer():
            yield DDSButton("Home", classes="wide", id="home")
            #yield DDSButton("Login", classes="wide", id="login")
            #yield DDSButton("Re-authenticate", classes="wide", id="re-authenticate")
    


class DDSAuthMenu(DDSContainer):
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
