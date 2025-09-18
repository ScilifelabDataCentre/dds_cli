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
import threading
import time


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
        self.download_thread: Optional[threading.Thread] = None
        self._stop_download = threading.Event()
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
                #disabled=not self.selected_project_id or self.is_downloading,
            )
            yield DDSButton(
                "Cancel download",
                id="cancel-download-button",
                #disabled=not self.is_downloading,
                #variant="error",
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

    def on_unmount(self) -> None:
        """On unmount, clean up any ongoing downloads."""
        if self.download_thread and self.download_thread.is_alive():
            self._stop_download.set()
            if self.downloader:
                self.downloader.cancel_download()
        
        self.is_downloading = False

    def watch_selected_project_id(self, selected_project_id: Optional[str]) -> None:
        """Watch the app's selected_project_id state and sync to local reactive attribute."""
        self.selected_project_id = selected_project_id

    def on_button_pressed(self, event: events.Click) -> None:
        """Handle button presses."""
        if event.button.id == "download-project-content-button":
            self._start_download()
        elif event.button.id == "cancel-download-button":
            self._cancel_download()

    def _start_download(self) -> None:
        """Start the download process."""
        print(f"[DEBUG] _start_download called")
        
        if self.is_downloading:
            print(f"[DEBUG] Already downloading, returning")
            return
            
        if not self.selected_project_id:
            print(f"[DEBUG] No project selected")
            self.app.notify("No project selected", severity="error")
            return
            
        print(f"[DEBUG] Starting download for project: {self.selected_project_id}")
        
        # Reset state
        self.status = "Initializing..."
        self.progress = 0.0
        self.files_downloaded = 0
        self.total_files = 0
        self.is_downloading = True
        self._stop_download.clear()
        
        # Start initialization and download in background thread
        project_id = self.selected_project_id
        print(f"[DEBUG] Creating thread for initialization and download...")
        self.download_thread = threading.Thread(target=self._full_download_worker, args=(project_id,), daemon=True)
        self.download_thread.start()
        print(f"[DEBUG] Download thread started")

    def _full_download_worker(self, project_id: str) -> None:
        """Complete worker function for initialization and downloading."""
        try:
            print(f"[DEBUG] Starting full download worker for project: {project_id}")
            
            # Initialize downloader
            print(f"[DEBUG] Creating ProjectDownloader...")
            self.downloader = ProjectDownloader(project=project_id)
            print(f"[DEBUG] ProjectDownloader created")
            
            # Set up callbacks
            print(f"[DEBUG] Setting up callbacks...")
            self.downloader.set_progress_callback(self._on_progress_update)
            self.downloader.set_file_completed_callback(self._on_file_completed)
            self.downloader.set_error_callback(self._on_error)
            print(f"[DEBUG] Callbacks set up")

            # Initialize
            print(f"[DEBUG] Starting initialization...")
            if not self.downloader.initialize(get_all=True):
                print(f"[DEBUG] Initialization failed")
                self._update_status("Initialization failed")
                return
            print(f"[DEBUG] Initialization successful")

            # Start download
            self._update_status("Starting download...")
            print(f"[DEBUG] Starting download_all...")
            
            # Start download in a separate thread so we can monitor cancellation
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(self.downloader.download_all, 4)
                
                # Monitor the download with cancellation checks
                while not future.done():
                    try:
                        success = future.result(timeout=0.1)
                        break
                    except concurrent.futures.TimeoutError:
                        # Check if download was cancelled
                        if self._stop_download.is_set():
                            print(f"[DEBUG] Download cancelled during execution")
                            self.downloader.cancel_download()
                            success = False
                            break
                        continue
            
            print(f"[DEBUG] Download completed with success: {success}")
            
            if success:
                self._update_status("Download completed")
            else:
                self._update_status("Download failed")
                
        except Exception as e:
            print(f"[DEBUG] Exception in full download worker: {e}")
            import traceback
            traceback.print_exc()
            self._update_status(f"Download failed: {e}")
        finally:
            # Reset state on main thread
            try:
                self.app.call_from_thread(self._reset_download_state)
            except Exception as e:
                print(f"[DEBUG] Error resetting state: {e}")
                # Fallback: try direct assignment
                try:
                    self.is_downloading = False
                    self.download_thread = None
                except Exception as e2:
                    print(f"[DEBUG] Direct reset also failed: {e2}")

    def _update_status(self, status: str) -> None:
        """Update status from worker thread."""
        print(f"[DEBUG] Updating status to: {status}")
        try:
            self.app.call_from_thread(lambda: setattr(self, 'status', status))
        except Exception as e:
            print(f"[DEBUG] Error updating status: {e}")
            # Fallback: try direct assignment (not thread-safe but might work)
            try:
                self.status = status
            except Exception as e2:
                print(f"[DEBUG] Direct assignment also failed: {e2}")

    def _reset_download_state(self) -> None:
        """Reset download state on main thread."""
        self.is_downloading = False
        self.download_thread = None

    def _on_progress_update(self, progress: DownloadProgress) -> None:
        """Handle progress updates from the downloader."""
        # Update UI on main thread
        self.app.call_from_thread(self._update_progress_ui, progress)
    
    def _update_progress_ui(self, progress: DownloadProgress) -> None:
        """Update progress UI on main thread."""
        self.progress = progress.overall_percentage / 100.0
        self.status = progress.status.title()
        self.files_downloaded = progress.completed_files
        self.total_files = progress.total_files

    def _on_file_completed(self, result: DownloadResult) -> None:
        """Handle file completed from the downloader."""
        pass  # We don't need to do anything special for individual files

    def _on_error(self, error: str) -> None:
        """Handle error from the downloader."""
        self._update_status(f"Error: {error}")
    
    def _cancel_download(self) -> None:
        """Cancel the ongoing download."""
        if self.is_downloading:
            # Signal stop
            self._stop_download.set()
            
            # Cancel the downloader if it exists
            if self.downloader:
                self.downloader.cancel_download()
            
            # Update status
            self.status = "Download cancelled"
            self.is_downloading = False
            
            # Notify user
            self.app.notify("Download cancelled by user", severity="warning")
