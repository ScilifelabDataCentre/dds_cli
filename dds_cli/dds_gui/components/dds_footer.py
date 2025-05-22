"""DDS Footer Widget"""

from textual.widgets import Footer


class DDSFooter(Footer):
    """DDS footer widget."""

    DEFAULT_CSS = """
    DDSFooter {
        FooterKey {
            &:hover {
                background: #43858B;
            }
        }
    }
    """
