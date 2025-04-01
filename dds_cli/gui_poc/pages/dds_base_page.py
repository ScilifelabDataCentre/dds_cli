"""DDS Base Page Widget"""

from typing import Any
from textual import events
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widget import Widget
from textual.widgets import ContentSwitcher, Label

from dds_cli.gui_poc.components.dds_button import DDSButton
from dds_cli.gui_poc.components.dds_container import DDSContainer
from dds_cli.gui_poc.pages.dds_home import DDSHomePage


class DDSBasePage(Widget):
    """A base page widget for the GUI. Handles the menu and content switching."""

    def __init__(self) -> None:
        super().__init__()

    DEFAULT_CSS = """
    DDSSidebar {
        width: 20%;
    }
    """

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield DDSSidebar()
            with ContentSwitcher(initial="home", id="dds-content-switcher"):
                yield DDSHomePage(id="home")
                yield DDSContent(Label("Login"), "Login", id="login")

    def on_button_pressed(self, event: events.Click) -> None:
        """Handle button presses."""
        if event.button.id == "home":
            self.query_one(ContentSwitcher).current = "home"
        elif event.button.id == "login":
            self.query_one(ContentSwitcher).current = "login"


class DDSSidebar(Widget):
    """A sidebar widget for the GUI."""

    def __init__(self) -> None:
        super().__init__()

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
    DDSMenu {
        align: center top;
    }

    DDSMenu > * {
        margin: 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield DDSButton("Home", id="home")
        yield DDSButton("Login", id="login")


class DDSAuthMenu(DDSContainer):
    """An auth menu widget for the GUI."""

    def __init__(self, title: str, *args: Any, **kwargs: Any) -> None:
        super().__init__(title=title, *args, **kwargs)

    DEFAULT_CSS = """
    DDSAuthMenu {
        align: center top;
    }
    """

    def compose(self) -> ComposeResult:
        yield DDSButton("Login")


class DDSContent(DDSContainer):
    """A content widget for the GUI."""

    def __init__(self, content: Widget, title: str, *args: Any, **kwargs: Any) -> None:
        super().__init__(title=title, *args, **kwargs)
        self.content = content

    def compose(self) -> ComposeResult:
        yield self.content
