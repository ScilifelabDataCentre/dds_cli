from typing import Any
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Label
from dds_cli.gui_poc.components.dds_modal import DDSModal
from dds_cli.gui_poc.components.dds_text_item import DDSTextItem, DDSTextTitle, DDSTextSubtitle
from dds_cli.gui_poc.pages.authentication.authentication_form import AuthenticationForm


class LoginModal(DDSModal):
    """A widget for the Login page."""
    def __init__(self, token_path: str, *args: Any, **kwargs: Any):
        super().__init__(title="Login", content=LoginModalContent(token_path), *args, **kwargs)
        self.token_path = token_path

class LoginModalContent(Widget):
    """A widget for the Login page."""
    def __init__(self, token_path: str, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.token_path = token_path

    DEFAULT_CSS = """
    #login-label {
        padding-left: 1;
        padding-right: 1;
        width: 100%;
    }
    """

    def compose(self) -> ComposeResult:
        yield Label("Login to your DDS account. Enter your email and password to get the two-factor authentication code.", id="login-label")
        yield AuthenticationForm(self.token_path, )
