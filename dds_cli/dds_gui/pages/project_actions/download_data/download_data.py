"""Download data widget for the DDS GUI."""

from typing import Any, Optional
import threading
import logging

from textual.app import ComposeResult
from textual.widget import Widget
from textual import events
from textual.reactive import reactive
from textual.widgets import Label, ProgressBar

from dds_cli.dds_gui.components.dds_container import (
    DDSSpacedContainer,
    DDSSpacedHorizontalContainer,
)
from dds_cli.dds_gui.components.dds_button import DDSButton
from dds_cli.dds_gui.pages.project_actions.download_data.project_downloader import (
    DownloadProgress,
    DownloadResult,
    ProjectDownloader,
)
from dds_cli.exceptions import (
    AuthenticationError,
    TokenNotFoundError,
    ApiRequestError,
    DownloadError,
)

# Logger
LOG = logging.getLogger(__name__)


class DownloadData(Widget):
    """A widget for downloading data."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the DownloadData widget."""
        super().__init__(*args, **kwargs)
        self.downloader: Optional[ProjectDownloader] = None
        self.download_thread: Optional[threading.Thread] = None
        self._stop_download = threading.Event()

    progress = reactive(0.0)
    files_downloaded = reactive(0)
    error_files = reactive(0)
    total_files = reactive(0)
    status = reactive(None)
    progress_status = reactive(None)

    # Local reactive attributes that mirror app state and trigger recomposition
    selected_project_id: reactive[Optional[str]] = reactive(None, recompose=True)
    is_downloading: reactive[bool] = reactive(False)

    def _safe_ui_operation(self, operation: callable, error_message: str = "UI operation failed") -> None:
        """Safely execute UI operations with consistent error handling."""
        try:
            operation()
        except RuntimeError as error:
            if "not running" in str(error).lower():
                return  # App is shutting down, ignore
            # Only log if it's not a missing element error (common during mounting/unmounting)
            if "no nodes match" not in str(error).lower():
                LOG.warning(f"Runtime error during {error_message}: %s", error)
        except Exception as error:
            # Only log if it's not a missing element error
            if "no nodes match" not in str(error).lower():
                LOG.warning(f"Error during {error_message}: %s", error)

    DEFAULT_CSS = """
    DownloadData {
        height: auto;
        width: 100%;
    }

    #files-label.disabled {
        color: $primary;
    }

    #progress-bar.disabled {
        color: $primary;
    }
    """

    def compose(self) -> ComposeResult:
        with DDSSpacedContainer(id="download-data-container", align="left middle"):
            yield DDSButton(
                "Download project content",
                id="download-project-content-button",
                disabled=not self.selected_project_id or self.is_downloading,
            )

            with DDSSpacedHorizontalContainer(id="progress-bar-container"):
                yield ProgressBar(
                    show_eta=False,
                    id="progress-bar",
                    total=100,
                    show_percentage=True,
                    classes="disabled",
                )
                yield Label(
                    f"Files: {self.files_downloaded}/{self.total_files}",
                    id="files-label",
                    classes="disabled",
                )

    def on_mount(self) -> None:
        """On mount, sync initial state and set up watchers."""
        # Initialize local reactive attributes with current app state
        self.selected_project_id = self.app.selected_project_id

        # Set up watchers to keep local state in sync with app state
        self.watch(self.app, "selected_project_id", self.watch_selected_project_id)

        # Set up watchers for reactive attributes to update labels manually
        self.watch(self, "files_downloaded", self.watch_files_downloaded)
        self.watch(self, "error_files", self.watch_error_files)
        self.watch(self, "total_files", self.watch_total_files)
        self.watch(self, "is_downloading", self.watch_is_downloading)

    def on_unmount(self) -> None:
        """On unmount, clean up any ongoing downloads."""
        # Signal stop immediately
        self._stop_download.set()

        # Cancel the downloader if it exists
        if self.downloader:
            try:
                self.downloader.cancel_download()
            except (DownloadError, ApiRequestError, OSError) as error:
                LOG.warning("Error cancelling download during unmount: %s", error)
            except Exception as error: # pylint: disable=broad-exception-caught
                LOG.error("Unexpected error cancelling download during unmount: %s", error)

        # Wait for download thread to finish (with timeout)
        if self.download_thread and self.download_thread.is_alive():
            self.download_thread.join(timeout=1.0)  # Reduced timeout to 1 second

        self.is_downloading = False

    def watch_selected_project_id(self, selected_project_id: Optional[str]) -> None:
        """Watch the app's selected_project_id state and sync to local reactive attribute."""
        self.selected_project_id = selected_project_id
        # Also update button state when project selection changes
        self.watch_is_downloading(self.is_downloading)

    def watch_files_downloaded(self, files_downloaded: int) -> None:
        """Watch files_downloaded changes and update the files label."""
        def update_label():
            files_label = self.query_one("#files-label", None)
            if files_label:
                if self.error_files > 0:
                    files_label.update(
                        f"Files: {files_downloaded}/{self.total_files} "
                        f"(❌ Errors: {self.error_files})"
                    )
                else:
                    files_label.update(f"Files: {files_downloaded}/{self.total_files}")
        
        self._safe_ui_operation(update_label, "files label update")

    def watch_error_files(self, error_files: int) -> None:
        """Watch error_files changes and update the files label."""
        def update_label():
            files_label = self.query_one("#files-label", None)
            if files_label:
                if error_files > 0:
                    files_label.update(
                        f"Files: {self.files_downloaded}/{self.total_files} "
                        f"(❌ Errors: {error_files})"
                    )
                else:
                    files_label.update(f"Files: {self.files_downloaded}/{self.total_files}")
        
        self._safe_ui_operation(update_label, "files label update")

    def watch_total_files(self, total_files: int) -> None:
        """Watch total_files changes and update the files label."""
        def update_label():
            files_label = self.query_one("#files-label", None)
            if files_label:
                if self.error_files > 0:
                    files_label.update(
                        f"Files: {self.files_downloaded}/{total_files} "
                        f"(❌ Errors: {self.error_files})"
                    )
                else:
                    files_label.update(f"Files: {self.files_downloaded}/{total_files}")
        
        self._safe_ui_operation(update_label, "files label update")

    def watch_is_downloading(self, is_downloading: bool) -> None:
        """Watch is_downloading changes and update the button state."""
        def update_button():
            button = self.query_one("#download-project-content-button", None)
            if button:
                button.disabled = not self.selected_project_id or is_downloading
        
        self._safe_ui_operation(update_button, "button state update")

    def on_button_pressed(self, event: events.Click) -> None:
        """Handle button presses."""
        def handle_button():
            if event.button.id == "download-project-content-button":
                self.query_one("#progress-bar", None).classes = "enabled"
                self.query_one("#files-label", None).classes = "enabled"
                self._start_download()
        
        self._safe_ui_operation(handle_button, "button press handling")

    def _start_download(self) -> None:
        """Start the download process."""
        if self.is_downloading:
            return

        if not self.selected_project_id:
            self.app.notify("No project selected", severity="error")
            return

        # Set up download destination
        # Reset state only when starting a new download
        self.progress = 0.0
        self.files_downloaded = 0
        self.error_files = 0
        self.total_files = 0
        self.is_downloading = True
        self._stop_download.clear()

        # Start initialization and download in background thread
        project_id = self.selected_project_id
        self.download_thread = threading.Thread(
            target=self._full_download_worker, args=(project_id,), daemon=True
        )
        self.download_thread.start()

    def _full_download_worker(self, project_id: str) -> None:
        """Complete worker function for initialization and downloading."""
        try:
            if self._stop_download.is_set():
                return

            # Initialize downloader
            self.downloader = ProjectDownloader(project=project_id)
            self.downloader.set_progress_callback(self._on_progress_update)
            self.downloader.set_file_completed_callback(self._on_file_completed)
            self.downloader.set_error_callback(self._on_error)

            # Initialize and download
            if not self.downloader.initialize(get_all=True):
                self._update_status("Failed to initialize download")
                return

            if self._stop_download.is_set():
                return

            self._update_status("Starting download...")
            
            if self._stop_download.is_set():
                return
                
            success = self.downloader.download_all(4)
            self._update_status("Download completed" if success else "Download failed")

        except (AuthenticationError, TokenNotFoundError) as error:
            self._update_status(f"Authentication failed: {error}")
            LOG.error("Authentication error during download: %s", error)
        except (ApiRequestError, DownloadError) as error:
            self._update_status(f"Download failed: {error}")
            LOG.error("Download error: %s", error)
        except (OSError, RuntimeError) as error:
            self._update_status(f"System error: {error}")
            LOG.error("System error during download: %s", error)
        except Exception as error:
            self._update_status(f"Unexpected error: {error}")
            LOG.error("Unexpected error during download: %s", error)
        finally:
            self._reset_download_state()

    def _update_status(self, status: str) -> None:
        """Update status from worker thread."""
        def update_status():
            if hasattr(self, "app") and self.app.is_running:
                self.app.call_from_thread(lambda: setattr(self, "status", status))
        
        self._safe_ui_operation(update_status, "status update")

    def _reset_download_state(self) -> None:
        """Reset download state on main thread."""
        def reset_state():
            try:
                if hasattr(self, "app") and self.app.is_running:
                    self.app.call_from_thread(lambda: setattr(self, "is_downloading", False))
                    self.app.call_from_thread(lambda: setattr(self, "download_thread", None))
                else:
                    self.is_downloading = False
                    self.download_thread = None
            except Exception:
                # Fallback for test scenarios or when app is not available
                self.is_downloading = False
                self.download_thread = None
        
        self._safe_ui_operation(reset_state, "download state reset")

    def _on_progress_update(self, progress: DownloadProgress) -> None:
        """Handle progress updates from the downloader."""
        def update_progress():
            if hasattr(self, "app") and self.app.is_running:
                self.app.call_from_thread(self._update_progress_ui, progress)
        
        self._safe_ui_operation(update_progress, "progress update")

    def _update_progress_ui(self, progress: DownloadProgress) -> None:
        """Update progress UI on main thread."""
        # Update reactive attributes
        self.progress = progress.overall_percentage
        self.files_downloaded = progress.completed_files
        self.error_files = progress.error_files
        self.total_files = progress.total_files
        self.progress_status = progress.status

        # Update progress bar
        def update_progress_bar():
            progress_bar = self.query_one("#progress-bar", None)
            if progress_bar:
                progress_bar.update(progress=progress.overall_percentage)
        
        self._safe_ui_operation(update_progress_bar, "progress bar update")

        # Send notifications
        self._send_progress_notifications(progress)

    def _send_progress_notifications(self, progress: DownloadProgress) -> None:
        """Send appropriate notifications based on progress status."""
        def send_notifications():
            if self.progress_status == "preparing" and not self.status == "preparing":
                self.app.notify("⏳ Preparing to download project content", severity="info")
                self.status = "preparing"
            elif (
                self.progress_status == "completed"
                and self.progress == 100
                and not self.status == "completed"
            ):
                self.app.notify("✅ Project content downloaded successfully", severity="info")
                self.status = "completed"
            elif self.error_files == 1 and not self.status == "error":
                self.app.notify(
                    "⚠️ Error downloading project content, please contact support",
                    severity="error",
                    timeout=10,
                )
                self.status = "error"
        
        self._safe_ui_operation(send_notifications, "progress notifications")

    def _on_file_completed(self, result: DownloadResult) -> None:
        """Handle file completed from the downloader."""
        # Individual file completion is handled by progress updates
        pass

    def _on_error(self, error: str) -> None:
        """Handle error from the downloader."""
        self._update_status(f"Error: {error}")
