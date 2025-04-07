"""DDS Home Page Widget"""

from typing import Any
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Label, RichLog, Static
from dds_cli.gui_poc.components.dds_container import DDSContainer
from dds_cli.gui_poc.components.dds_text_item import (
    DDSTextItem,
    DDSTextList,
    DDSTextSubtitle,
    DDSTextTitle,
)


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
        with Container(id="home-content"):
            yield DDSTextTitle("Welcome to the DDS GUI")
            yield DDSTextSubtitle("SciLifeLab Data Delivery System (DDS) graphical user interface")
            yield DDSTextList(
                [
                    "Access token is saved in a .dds_cli_token file in the home directory.",
                    "The token is valid for 7 days. Make sure your token is valid long enough for the delivery to finish.",
                    "To avoid that a delivery fails because of an expired token, we recommend re-authenticating yourself before each delivery.",
                ]
            )
            yield DDSTextItem(
                "More information can be found by typing ^h or clicking on the help in the application footer."
            )


class DDSMOTD(DDSContainer):
    """A widget for the MOTD."""

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(title="Important information", classes="accent", *args, **kwargs)

    def compose(self) -> ComposeResult:
        yield DDSTextItem(MOTD_1)
        yield DDSTextItem(MOTD_2)


class DDSIcon(Horizontal):
    """A widget for the icon."""

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)

    DEFAULT_CSS = """
    DDSIcon {
        height: auto;
        color: $accent;  

    }
    """

    def compose(self) -> ComposeResult:
            yield Static(
"""     ︵          
 ︵ (  )   ︵     
(  ) ) (  (  )   
 ︶  (  ) ) (    
      ︶ (  )        
          ︶""",
                id="dds-icon",
            )
        