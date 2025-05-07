"""DDS Project Information Widget"""

from typing import Any
from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Label, Static
from dds_cli.gui_poc.components.dds_container import DDSContainer, DDSContentContainer, DDSSpacedContainer
from dds_cli.gui_poc.components.dds_key_pair_table import DDSKeyPairTable

MOCK_PROJECT_INFORMATION = [
    ("Project id", "Project id"),
    ("Created by", "Project Status"),
    ("Status", "Project Created"),
    ("Last updated", "Project Updated"),
    ("Size", "Project Size"),
    ("Support contact", "Project Support Contact"),
]

class DDSProjectInformation(DDSContainer):
    """A widget for the project information."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

    def compose(self) -> ComposeResult:
        with DDSSpacedContainer():
            with DDSContentContainer():    
                yield Label("[b]Project Title:[/b] Test Title")
                yield Label("[b]Project Description:[/b] Test Description")
            yield DDSKeyPairTable(MOCK_PROJECT_INFORMATION, id="project-information-table")