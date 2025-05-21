"""DDS Login modal."""

from typing import Any
from textual.containers import Vertical
from textual.widget import Widget
from textual.widgets import Label

from dds_cli.gui_poc.components.dds_modal import DDSModal
from dds_cli.gui_poc.pages.authentication.authentication_form import AuthenticationForm


class LoginModal(DDSModal):
    """A widget for the Login page."""

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(title="Login", content=self.create_content(), *args, **kwargs)

    DEFAULT_CSS = """
    #login-label {
        padding-left: 1;
        padding-right: 1;
        width: 100%;
    }
    """

    def create_content(self) -> Widget:
        """Create the content of the modal."""
        return Vertical(
            Label(
                "Login to your DDS account. Enter your email and password to get the two-factor authentication code.",
                id="login-label",
            ),
            AuthenticationForm(self.close_modal),
            id="login-modal-content",
        )
