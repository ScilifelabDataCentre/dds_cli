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
from dds_cli import exceptions as dds_cli_exceptions
from typing import Any, Optional
import asyncio
import concurrent.futures


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


class CancelDownloadMessage(Message):
    """Message sent to cancel download."""
    def __init__(self) -> None:
        super().__init__()



class DownloadData(Widget):
    """A widget for downloading data."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.downloader: Optional[ProjectDownloader] = None
        self.download_worker = None
        # Initialize reactive attributes with default values
        self.selected_project_id = None
        self.is_downloading = False

    progress = reactive(0.0, recompose=True)
    status = reactive("Ready", recompose=True)
    files_downloaded = reactive(0, recompose=True)
    total_files = reactive(0, recompose=True)
    # Local reactive attributes that mirror app state and trigger recomposition
    selected_project_id: reactive[Optional[str]] = reactive(None, recompose=True)
    is_downloading: reactive[bool] = reactive(False, recompose=True)

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
                disabled=not self.selected_project_id or self.is_downloading,
            )
            yield DDSButton(
                "Cancel download",
                id="cancel-download-button",
                disabled=not self.is_downloading,
                variant="error",
            )
            yield Label(f"Progress: {self.progress:.1%}", id="progress-label")
            yield Label(f"Files: {self.files_downloaded}/{self.total_files}", id="files-label")
            yield Label(f"Status: {self.status}", id="status-label")

    def on_mount(self) -> None:
        """On mount, sync initial state and set up watchers."""
        # Initialize local reactive attributes with current app state
        self.selected_project_id = self.app.selected_project_id
        
        # Set up watchers to keep local state in sync with app state
        self.watch(self.app, "selected_project_id", self.watch_selected_project_id)

    def watch_selected_project_id(self, selected_project_id: Optional[str]) -> None:
        """Watch the app's selected_project_id state and sync to local reactive attribute."""
        self.selected_project_id = selected_project_id

    def on_button_pressed(self, event: events.Click) -> None:
        """Handle button presses."""
        if event.button.id == "download-project-content-button":
            # Update status and start download
            self.status = "Initializing..."
            self.progress = 0.0
            self.files_downloaded = 0
            self.total_files = 0
            self.is_downloading = True
            # Force UI update before starting worker
            self.refresh()
            self.download_worker = self.run_worker(self._initialize_and_download_worker(), name="download")
        elif event.button.id == "cancel-download-button":
            # Cancel the download via message system
            self.post_message(CancelDownloadMessage())

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
            
            # Update button states via message to main thread
            self.post_message(StatusUpdateMessage("Download ready"))

            # Start the actual download in a separate thread to avoid blocking
            # Run download_all in a thread pool to avoid blocking the worker
            
            with concurrent.futures.ThreadPoolExecutor() as executor:
                # Submit the download task
                future = executor.submit(self.downloader.download_all, 4)
                
                # Wait for completion with periodic yielding
                while not future.done():
                    try:
                        success = future.result(timeout=0.1)
                        break
                    except concurrent.futures.TimeoutError:
                        # Check if download was cancelled
                        if self.downloader and self.downloader._cancelled:
                            print("[WORKER] Download was cancelled")
                            success = False
                            break
                        # Yield control to allow message processing
                        await asyncio.sleep(0.01)
                        continue
            
            if success:
                self.app.notify("Download completed successfully", severity="information")
                self.post_message(StatusUpdateMessage("Download completed"))
            else:
                self.app.notify("Download failed or was cancelled", severity="error")
                self.post_message(StatusUpdateMessage("Download failed"))
            
            # Reset download state when download completes
            self.is_downloading = False
            self.download_worker = None

        except (
            dds_cli_exceptions.DownloadError,
            dds_cli_exceptions.AuthenticationError,
            dds_cli_exceptions.TokenNotFoundError,
            dds_cli_exceptions.ApiRequestError,
            ValueError,
            OSError,
            RuntimeError,
            dds_cli_exceptions.DDSCLIException,
        ) as e:
            self.app.notify(f"Download failed: {e}", severity="error")

            # Reset download state on error
            self.is_downloading = False
            self.download_worker = None
            self.post_message(StatusUpdateMessage("Download failed"))

    def _on_progress_update(self, progress: DownloadProgress) -> None:
        """Handle progress updates from the downloader."""
        # Post message to main thread for thread-safe UI update
        self.post_message(ProgressUpdateMessage(progress))
    
    def on_progress_update_message(self, message: ProgressUpdateMessage) -> None:
        """Handle progress update messages on the main thread."""
        progress = message.progress
        self.progress = progress.overall_percentage / 100.0  # Convert percentage to 0.0-1.0 range
        self.status = progress.status.title()  # Use status from DownloadProgress class
        self.files_downloaded = progress.completed_files
        self.total_files = progress.total_files
    
    def on_status_update_message(self, message: StatusUpdateMessage) -> None:
        """Handle status update messages on the main thread."""
        self.status = message.status
    
    def on_cancel_download_message(self, message: CancelDownloadMessage) -> None:
        """Handle cancel download messages on the main thread."""
        self._cancel_download()
    
    
    def _on_file_completed(self, result: DownloadResult) -> None:
        """Handle file completed from the downloader."""
        #self.app.notify(f"File completed: {result.file_path}", severity="information")

    def _on_error(self, error: str) -> None:
        """Handle error from the downloader."""
        self.app.notify(f"Error: {error}", severity="error")

    def _cancel_download(self) -> None:
        """Cancel the ongoing download."""
        if self.downloader and self.is_downloading:
            # Cancel the downloader
            self.downloader.cancel_download()
            
            # Cancel the worker thread if it exists
            if self.download_worker:
                self.download_worker.cancel()
                self.download_worker = None
            
            # Update status
            self.status = "Download cancelled"
            self.app.notify("Download cancelled", severity="information")
            
            # Reset download state
            self.is_downloading = False