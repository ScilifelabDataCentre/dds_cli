from typing import Any
from textual.app import ComposeResult
from dds_cli.gui_poc.components.dds_container import DDSContainer
from dds_cli.gui_poc.components.dds_text_item import DDSTextSubtitle, DDSTextTitle
from dds_cli.gui_poc.components.dds_form import DDSForm
from dds_cli.gui_poc.pages.authentication.authentication_form import AuthenticationForm

class DDSReAuthenticatePage(DDSContainer):
    """A widget for the Re-authenticate page."""
    def __init__(self, token_path: str, *args: Any, **kwargs: Any):
        super().__init__(title="Re-authenticate", *args, **kwargs)  
        self.token_path = token_path

    def compose(self) -> ComposeResult:
        yield DDSTextTitle("Re-authenticate")
        yield DDSTextSubtitle("Please enter your credentials to re-authenticate with the DDS.")
        yield AuthenticationForm(self.token_path)


