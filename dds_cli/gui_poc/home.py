from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widget import Widget
from textual.widgets import Label

import dds_cli

DDS_URL = dds_cli.DDSEndpoint.BASE_ENDPOINT
DDS_URL_BASE = DDS_URL[: DDS_URL.index("/", 8)]


class HomeScreen(Widget):
    
    def compose(self) -> ComposeResult:
        with Vertical(id="home-screen"):
            yield Label("SciLifeLab Data Delivery System", id="title")
            yield Label(f"{DDS_URL_BASE}", id="url")
            yield Label(f"CLI Version: {dds_cli.__version__}", id="version")
