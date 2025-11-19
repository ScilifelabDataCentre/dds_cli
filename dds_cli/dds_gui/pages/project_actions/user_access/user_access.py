"""DDS User Access Widget"""

from typing import Any
from textual.app import ComposeResult
from textual.widget import Widget

from dds_cli.dds_gui.components.dds_button import DDSButton
from dds_cli.dds_gui.components.dds_container import (
    DDSSpacedContainer,
    DDSSpacedHorizontalContainer,
)
from dds_cli.dds_gui.components.dds_input import DDSInput
from dds_cli.dds_gui.components.dds_text_item import DDSTextItem


class UserAccess(Widget):
    """A widget for user access."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

    DEFAULT_CSS = """
    UserAccess {
        height: auto;
        width: 100%;
    }
    """

    def compose(self) -> ComposeResult:
        with DDSSpacedContainer(id="user-access-container"):
            yield DDSTextItem(
                "Manage user access by inviting users, revoke access, or re-granting access to projects."
            )
            if self.app.selected_project_id:
                yield DDSInput(placeholder="Enter email address")
                with DDSSpacedHorizontalContainer(id="user-access-buttons"):
                    yield DDSButton("Invite User")
                    yield DDSButton("Revoke Access")
                    yield DDSButton("Re-grant Access")
            else:
                yield DDSTextItem("No project selected.")
