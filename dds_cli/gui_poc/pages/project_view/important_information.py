"""DDS Important Information Widget"""

from typing import Any
from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Collapsible, Label, Static
from dds_cli.gui_poc.components.dds_button import DDSSkinnyButton
from dds_cli.gui_poc.components.dds_container import (
    DDSContainer,
    DDSContentContainer,
    DDSSpacedContainer,
)

IMPORTANT_INFORMATION_MESSAGES = [{
    "Created": "2025-02-07 11:13",
    "Message": "Important! Data download on Dardel: For data downloads on Dardel, please log into the dedicated file transfer node: dardel-ftn01.pdc.kth.se. Do NOT submit data-transfer jobs to the queueing system, run them directly on that node."
}, {
    "Created": "2025-02-07 11:13",
    "Message": "Important! Data download on Dardel: For data downloads on Dardel, please log into the dedicated file transfer node: dardel-ftn01.pdc.kth.se. Do NOT submit data-transfer jobs to the queueing system, run them directly on that node."
}
    ]


class ImportantInformation(DDSContainer):
    """A widget for the important information/motd"""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

    DEFAULT_CSS = """
    DDSContentContainer {
        margin-bottom: 1;
    }
    .important-information-created {
       color: #E6FF3D;
       text-style: bold;
    }
    """

    def compose(self) -> ComposeResult:
        for message in IMPORTANT_INFORMATION_MESSAGES:
            with DDSContentContainer():
                yield Static(message["Created"], classes="important-information-created")
                yield Static(message["Message"], classes="important-information-message")
