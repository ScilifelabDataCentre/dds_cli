"""Important information widget"""

from typing import Any
from textual.app import ComposeResult

from dds_cli.dds_gui.components.dds_container import DDSContainer, DDSSpacedContainer
from dds_cli.dds_gui.pages.important_information.components.motd_card import MOTDCard


class ImportantInformation(DDSContainer):
    """Important information widget displaying message of the day"""
    def __init__(self, title: str, *args: Any, **kwargs: Any) -> None:
        super().__init__(title=title, *args, **kwargs)

    def compose(self) -> ComposeResult:
        with DDSSpacedContainer():
            yield MOTDCard("Important information", "This is the important information message of the day")
            yield MOTDCard("Important information", "This is the important information message of the day")
            yield MOTDCard("Important information", "This is the important information message of the day")
            yield MOTDCard("Important information", "This is the important information message of the day")