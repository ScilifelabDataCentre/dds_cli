from typing import Any
from textual.app import ComposeResult
from dds_cli.gui_poc.components.dds_container import DDSContainer
from dds_cli.gui_poc.components.dds_text_item import DDSTextTitle, DDSTextSubtitle
from dds_cli.gui_poc.pages.authentication.authentication_form import AuthenticationForm


class DDSLoginPage(DDSContainer):
    """A widget for the Login page."""
    def __init__(self, token_path: str, *args: Any, **kwargs: Any):
        super().__init__(title="Login", *args, **kwargs)
        self.token_path = token_path
    
    def compose(self) -> ComposeResult:
        yield DDSTextTitle("Login")
        yield DDSTextSubtitle("Please enter your credentials to authenticate with the DDS.")
        yield AuthenticationForm(self.token_path)
