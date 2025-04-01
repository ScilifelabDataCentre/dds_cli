"""DDS Home Page Widget"""

from typing import Any
from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Label, Static
from dds_cli.gui_poc.components.dds_container import DDSContainer


MOTD_1 = """2025-02-19 11:19 - If you are still experiencing issues when upload or download, specially if the error message includes something similar to 'AccessKeyInvalid', send us a support ticket at delivery@scilifelab.se. We're very sorry for this inconveniences."""
MOTD_2 = """2025-02-07 11:13 - Important! Data download on Dardel: For data downloads on Dardel, please log into the dedicated file transfer node: dardel-ftn01.pdc.kth.se. Do NOT submit data-transfer jobs to the queueing system, run them directly on that node."""


class DDSHomePage(Container):
    """A widget for the home page. Needs to be a container to allow for content switching."""

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)

    DEFAULT_CSS = """
    DDSHomeContent {
        height: 60%;
    }
    DDSMOTD {
        height: 40%;
    }
    """

    def compose(self) -> ComposeResult:
        yield DDSHomeContent()
        yield DDSMOTD()


class DDSHomeContent(DDSContainer):
    """A widget for the home page content."""

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(title="Home", *args, **kwargs)

    def compose(self) -> ComposeResult:
        yield Label("Home Content")


class DDSMOTD(DDSContainer):
    """A widget for the MOTD."""

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(title="MOTD", classes="accent", *args, **kwargs)

    DEFAULT_CSS = """
    Static {
        margin-bottom: 1;
        margin-right: 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static(MOTD_1)
        yield Static(MOTD_2)
