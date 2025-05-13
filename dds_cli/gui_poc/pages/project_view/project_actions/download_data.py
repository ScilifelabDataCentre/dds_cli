"""Download Data Widget"""

import time
from typing import Any
from textual import events
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Label, ProgressBar
from textual.timer import Timer
from dds_cli.gui_poc.components.dds_container import DDSSpacedContainer, DDSContentContainer, DDSSpacedHorizontalContainer
from dds_cli.gui_poc.components.dds_button import DDSButton
from dds_cli.gui_poc.components.dds_text_item import DDSTextItem

class DownloadData(Widget):
    """A widget for downloading data."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

    progress_timer: Timer

    DEFAULT_CSS = """
    DownloadData {
        border: round $secondary;
        height: 10fr;
    }

    """
        
    def compose(self) -> ComposeResult:
        with DDSSpacedContainer(id="download-data-container"):
            yield DDSTextItem("Download data from project by either downloading the whole project, or a specific file or sub-directory.")
            with DDSSpacedHorizontalContainer():
                yield DDSButton("Download project", id="download-project")
                yield DDSButton("Download selected")
            #yield ProgressBar()

    def on_button_pressed(self, event: events.Click) -> None:
        """Handle button presses."""
        if event.button.id == "download-project":
            self.query_one("#download-data-container").mount(ProgressBar())
            self.query_one("#download-project").disabled = True
            self.progress_timer = self.set_interval(1 / 10, self.make_progress, pause=True)
            self.query_one(ProgressBar).update(total=100)
            self.progress_timer.resume()
            
    def make_progress(self) -> None:
        """Called automatically to advance the progress bar."""
        self.query_one(ProgressBar).advance(1)