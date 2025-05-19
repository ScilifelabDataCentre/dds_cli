from typing import Any
from textual.app import ComposeResult
from textual.containers import Container
from textual.content import Content
from textual.widget import Widget, WidgetError
from dds_cli.gui_poc.components.dds_modal import DDSModal
from dds_cli.gui_poc.components.dds_text_item import DDSTextSubtitle, DDSTextTitle
from dds_cli.gui_poc.components.dds_form import DDSForm
from dds_cli.gui_poc.pages.authentication.authentication_form import AuthenticationForm
from textual.screen import ModalScreen





class ReAuthenticateModal(DDSModal):
    """A widget for the Re-authenticate page."""
    def __init__(self, token_path: str, *args: Any, **kwargs: Any):
        super().__init__(title="Re-authenticate", content=
                           ReAuthenticateModalContent(token_path)
                       , *args, **kwargs)  
        self.token_path = token_path

class ReAuthenticateModalContent(Widget):
    """A widget for the Re-authenticate page."""
    def __init__(self, token_path: str, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.token_path = token_path

    def compose(self) -> ComposeResult:
        yield AuthenticationForm(self.token_path)
