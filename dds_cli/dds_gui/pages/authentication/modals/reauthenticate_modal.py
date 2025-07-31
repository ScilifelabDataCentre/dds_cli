"""DDS Re-authenticate Modal"""

from typing import Any
from textual.containers import Vertical
from textual.widget import Widget
from textual.widgets import Label

from dds_cli.dds_gui.components.dds_modal import DDSModal
from dds_cli.dds_gui.pages.authentication.authentication_form import AuthenticationForm


class ReAuthenticateModal(DDSModal):
    """A widget for the Re-authenticate page."""

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(title="Re-authenticate", content=self.create_content(), *args, **kwargs)

    DEFAULT_CSS = """
    #reauthenticate-label {
        padding-left: 1;
        padding-right: 1;
        width: 100%;
    }
    """

    def create_content(self) -> Widget:
        """Create the content of the modal."""
        return Vertical(
            Label(
                "Re-authenticate yourself to the DDS. This will restore your session.",
                id="reauthenticate-label",
            ),
            AuthenticationForm(self.close_modal),
            id="reauthenticate-modal-content",
        )
