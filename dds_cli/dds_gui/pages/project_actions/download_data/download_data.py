"""Download data widget for the DDS GUI."""

from textual.app import ComposeResult
from textual.widget import Widget
from textual import events
from textual.reactive import reactive
from textual.widgets import Label
from textual.message import Message
from dds_cli.dds_gui.components.dds_container import DDSSpacedContainer
from dds_cli.dds_gui.components.dds_button import DDSButton
from dds_cli.dds_gui.utils.project_downloader import DownloadProgress, DownloadResult, ProjectDownloader

from typing import Any, Optional
import asyncio


class ProgressUpdateMessage(Message):
    """Message sent when download progress updates."""
    def __init__(self, progress: DownloadProgress) -> None:
        self.progress = progress
        super().__init__()


class StatusUpdateMessage(Message):
    """Message sent to update status."""
    def __init__(self, status: str) -> None:
        self.status = status
        super().__init__()



class DownloadData(Widget):
    """A widget for downloading data."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.downloader: Optional[ProjectDownloader] = None

    progress = reactive(0.0, recompose=True)
    status = reactive("Ready", recompose=True)

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
            yield Label(f"Progress: {self.progress:.1%}", id="progress-label")
            yield Label(f"Status: {self.status}", id="status-label")

    def on_button_pressed(self, event: events.Click) -> None:
        """Handle button presses."""
        if event.button.id == "download-project-content-button":
            # Update status and start download
            self.status = "Initializing..."
            self.progress = 0.0
            # Force UI update before starting worker
            self.refresh()
            self.run_worker(self._initialize_and_download_worker(), name="download")

    async def _initialize_and_download_worker(self) -> None:
        """Worker function for initializing downloader and starting download."""
        try:
            # Small delay to allow UI to update
            await asyncio.sleep(0.1)
            
            # Initialize downloader
            self.downloader = ProjectDownloader(
                project=self.app.selected_project_id
            )

            # Set up callbacks
            self.downloader.set_progress_callback(self._on_progress_update)
            self.downloader.set_file_completed_callback(self._on_file_completed)
            self.downloader.set_error_callback(self._on_error)

            if not self.downloader.initialize(get_all=True):
                self.app.notify("Error initializing downloader", severity="error")
                self.post_message(StatusUpdateMessage("Initialization failed"))
                return

            # Update status to show we're ready to download
            self.post_message(StatusUpdateMessage("Starting download..."))
            await asyncio.sleep(0.1)  # Allow UI to update

            # Start the actual download in a separate thread to avoid blocking
            print("[WORKER] Starting download_all...")
            
            # Run download_all in a thread pool to avoid blocking the worker
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                # Submit the download task
                future = executor.submit(self.downloader.download_all, 4)
                
                # Wait for completion with periodic yielding
                while not future.done():
                    try:
                        success = future.result(timeout=0.1)
                        break
                    except concurrent.futures.TimeoutError:
                        # Yield control to allow message processing
                        await asyncio.sleep(0.01)
                        continue
            
            print(f"[WORKER] Download completed: {success}")
            if success:
                self.app.notify("Download completed successfully", severity="information")
            else:
                self.app.notify("Download failed or was cancelled", severity="error")

        except (ValueError, OSError, RuntimeError) as e:
            self.app.notify(f"Download failed: {e}", severity="error")
            self.post_message(StatusUpdateMessage("Download failed"))

    def _on_progress_update(self, progress: DownloadProgress) -> None:
        """Handle progress updates from the downloader."""
        print(f"[WORKER] Progress callback: {progress.overall_percentage:.1f}% - {progress.status}")
        # Post message to main thread for thread-safe UI update
        self.post_message(ProgressUpdateMessage(progress))
    
    def on_progress_update_message(self, message: ProgressUpdateMessage) -> None:
        """Handle progress update messages on the main thread."""
        progress = message.progress
        self.progress = progress.overall_percentage / 100.0  # Convert percentage to 0.0-1.0 range
        self.status = progress.status.title()  # Use status from DownloadProgress class
    
    def on_status_update_message(self, message: StatusUpdateMessage) -> None:
        """Handle status update messages on the main thread."""
        self.status = message.status
    
    
    def _on_file_completed(self, result: DownloadResult) -> None:
        """Handle file completed from the downloader."""
        self.app.notify(f"File completed: {result.file_path}", severity="information")

    def _on_error(self, error: str) -> None:
        """Handle error from the downloader."""
        self.app.notify(f"Error: {error}", severity="error")