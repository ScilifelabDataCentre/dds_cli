"""Download data widget for the DDS GUI."""

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Button, ProgressBar, Static, Label
from textual import events

from dds_cli.dds_gui.components.dds_container import DDSSpacedContainer
from dds_cli.dds_gui.components.dds_button import DDSButton
from dds_cli.dds_gui.utils.project_downloader import DownloadProgress, DownloadResult, ProjectDownloader

from typing import Any, Optional

class DownloadData(Widget):
    """A widget for downloading data."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.downloader: Optional[ProjectDownloader] = None

    DEFAULT_CSS = """
    DownloadData {
        height: auto;
        width: 100%;
    }
    """

    def compose(self) -> ComposeResult:
        with DDSSpacedContainer(id="download-data-container", align="left middle"):
            yield DDSButton(
                "Download project content",
                id="download-project-content-button",
                disabled=not self.app.selected_project_id,
            )

    def on_button_pressed(self, event: events.Click) -> None:
        """Handle button presses."""
        if event.button.id == "download-project-content-button":
            self.initialize_and_start_download()

    def initialize_and_start_download(self) -> None:
        """Initialize the downloader and start the download."""
        if self.initialize_downloader(): # First initialize the downloader
            self.start_download() # Then start the download

    def initialize_downloader(self) -> bool:
        """Initialize the downloader. 
        Returns True if successful, False otherwise."""
        try: 
            self.downloader = ProjectDownloader(
                project=self.app.selected_project_id
            )

            # Set up callbacks
            self.downloader.set_progress_callback(self.on_progress_update)
            self.downloader.set_file_completed_callback(self.on_file_completed)
            self.downloader.set_error_callback(self.on_error)

            if self.downloader.initialize(get_all=True):
                return True
            else:
                return False
        
        except (ValueError, OSError, RuntimeError) as e:
            self.app.notify(f"Error initializing downloader: {e}", severity="error")
            return False

    def start_download(self) -> None:
        """Start the download."""

        # Start the download in a worker thread
        self.run_worker(self._download_worker(), name="download")

    def on_progress_update(self, progress: DownloadProgress) -> None:
        """Handle progress updates from the downloader."""
        self.app.notify(f"Progress: {progress.overall_progress:.1%} - {progress.status}", severity="information")

    def on_file_completed(self, result: DownloadResult) -> None:
        """Handle file completed from the downloader."""
        self.app.notify(f"File completed: {result.file_path}", severity="information")

    def on_error(self, error: str) -> None:
        """Handle error from the downloader."""
        self.app.notify(f"Error: {error}", severity="error")

    async def _download_worker(self) -> None:
        """Worker function for downloading."""
        try: 
            success = self.downloader.download_all(num_threads=4)
            if success:
                self.app.notify("Download completed successfully", severity="information")
            else:
                self.app.notify("Download failed or was cancelled", severity="error")
        except (ValueError, OSError, RuntimeError) as e:
            self.app.notify(f"Error downloading: {e}", severity="error")