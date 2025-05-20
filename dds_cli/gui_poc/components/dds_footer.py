from textual.widgets import Footer

class DDSFooter(Footer):
    """DDS footer widget."""

    DEFAULT_CSS = """
    DDSFooter {
    background: $panel;

    FooterKey {
        &:hover {
            background: #43858B;
        }
        
    }
    }
    """
