"""Download data widget for the DDS GUI."""

from textual.app import ComposeResult
from textual.widget import Widget
from textual import events
from textual.reactive import reactive
from textual.widgets import Label, ProgressBar
from textual.message import Message
from dds_cli.dds_gui.components.dds_container import DDSSpacedContainer, DDSSpacedHorizontalContainer
from dds_cli.dds_gui.components.dds_button import DDSButton
from dds_cli.dds_gui.utils.project_downloader import DownloadProgress, DownloadResult, ProjectDownloader
from dds_cli import exceptions as dds_cli_exceptions
from typing import Any, Optional
import threading
import time


class DownloadDataProgressBar(ProgressBar):
    """A progress bar for the download data widget."""
    
    


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

    progress = reactive(0.0)
    status = reactive("Ready")
    files_downloaded = reactive(0)
    error_files = reactive(0)
    total_files = reactive(0)
    # Local reactive attributes that mirror app state and trigger recomposition
    selected_project_id: reactive[Optional[str]] = reactive(None, recompose=True)
    is_downloading: reactive[bool] = reactive(False)

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
            #yield Label(f"Progress: {self.progress:.1%}", id="progress-label")
            #yield Label(f"Files: {self.files_downloaded}/{self.total_files}", id="files-label")

            with DDSSpacedHorizontalContainer(id="progress-bar-container"):
                yield ProgressBar(show_eta=False, id="progress-bar", total=100, show_percentage=True, classes="disabled")
                yield Label(f"Files: {self.files_downloaded}/{self.total_files} (Errors: {self.error_files})", id="files-label", classes="disabled")
            
            
    def on_mount(self) -> None:
        """On mount, sync initial state and set up watchers."""
        # Initialize local reactive attributes with current app state
        self.selected_project_id = self.app.selected_project_id
        
        # Set up watchers to keep local state in sync with app state
        self.watch(self.app, "selected_project_id", self.watch_selected_project_id)
        
        # Set up watchers for reactive attributes to update labels manually
        self.watch(self, "progress", self.watch_progress)
        self.watch(self, "status", self.watch_status)
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
            except Exception as e:
                pass  # Silently handle errors during unmount
        
        # Wait for download thread to finish (with timeout)
        if self.download_thread and self.download_thread.is_alive():
            self.download_thread.join(timeout=1.0)  # Reduced timeout to 1 second
        
        self.is_downloading = False

    def watch_selected_project_id(self, selected_project_id: Optional[str]) -> None:
        """Watch the app's selected_project_id state and sync to local reactive attribute."""
        self.selected_project_id = selected_project_id
        # Also update button state when project selection changes
        self.watch_is_downloading(self.is_downloading)

    def watch_progress(self, progress: float) -> None:
        """Watch progress changes and update the progress label."""
        try:
            progress_label = self.query_one("#progress-label", None)
            if progress_label:
                progress_label.update(f"Progress: {progress:.1%}")
        except Exception:
            pass  # Label might not exist yet

    def watch_status(self, status: str) -> None:
        """Watch status changes and update the status label."""
        try:
            status_label = self.query_one("#status-label", None)
            if status_label:
                status_label.update(f"Status: {status}")
        except Exception:
            pass  # Label might not exist yet

    def watch_files_downloaded(self, files_downloaded: int) -> None:
        """Watch files_downloaded changes and update the files label."""
        try:
            files_label = self.query_one("#files-label", None)
            if files_label:
                files_label.update(f"Files: {files_downloaded}/{self.total_files} (Errors: {self.error_files})")
        except Exception:
            pass  # Label might not exist yet

    def watch_error_files(self, error_files: int) -> None:
        """Watch error_files changes and update the files label."""
        try:
            files_label = self.query_one("#files-label", None)
            if files_label:
                files_label.update(f"Files: {self.files_downloaded}/{self.total_files} (Errors: {error_files})")
        except Exception:
            pass  # Label might not exist yet

    def watch_total_files(self, total_files: int) -> None:
        """Watch total_files changes and update the files label."""
        try:
            files_label = self.query_one("#files-label", None)
            if files_label:
                files_label.update(f"Files: {self.files_downloaded}/{total_files} (Errors: {self.error_files})")
        except Exception:
            pass  # Label might not exist yet

    def watch_is_downloading(self, is_downloading: bool) -> None:
        """Watch is_downloading changes and update the button state."""
        try:
            button = self.query_one("#download-project-content-button", None)
            if button:
                button.disabled = not self.selected_project_id or is_downloading
        except Exception:
            pass  # Button might not exist yet

    def on_button_pressed(self, event: events.Click) -> None:
        """Handle button presses."""
        try:
            if event.button.id == "download-project-content-button":
                self.query_one("#progress-bar", None).classes = "enabled"
                self.query_one("#files-label", None).classes = "enabled"
                self._start_download()
        except Exception as e:
            pass  # Silently handle errors

    def _start_download(self) -> None:
        """Start the download process."""
        if self.is_downloading:
            return
            
        if not self.selected_project_id:
            self.app.notify("No project selected", severity="error")
            return
        
        # Set up download destination
        # Reset state only when starting a new download
        self.status = "Initializing..."
        self.progress = 0.0
        self.files_downloaded = 0
        self.error_files = 0
        self.total_files = 0
        self.is_downloading = True
        self._stop_download.clear()
        
        # Start initialization and download in background thread
        project_id = self.selected_project_id
        self.download_thread = threading.Thread(target=self._full_download_worker, args=(project_id,), daemon=True)
        self.download_thread.start()

    def _full_download_worker(self, project_id: str) -> None:
        """Complete worker function for initialization and downloading."""
        try:
            # Check if we should stop before starting
            if self._stop_download.is_set():
                return
            
            # Initialize downloader
            self.downloader = ProjectDownloader(project=project_id)
            
            # Set up callbacks
            self.downloader.set_progress_callback(self._on_progress_update)
            self.downloader.set_file_completed_callback(self._on_file_completed)
            self.downloader.set_error_callback(self._on_error)

            # Initialize
            if not self.downloader.initialize(get_all=True):
                self._update_status("Initialization failed")
                return
            
            # Check if we should stop after initialization
            if self._stop_download.is_set():
                return

            # Start download
            self._update_status("Starting download...")
            
            # Check if we should stop before starting download
            if self._stop_download.is_set():
                return
            
            # Start download directly - the ProjectDownloader handles cancellation internally
            success = self.downloader.download_all(4)
            
            if success:
                self._update_status("Download completed")
            else:
                self._update_status("Download failed")
                
        except Exception as e:
            self._update_status(f"Download failed: {e}")
        finally:
            # Reset state on main thread
            try:
                # Check if app is still running before trying to reset state
                try:
                    if hasattr(self, 'app') and self.app.is_running:
                        self.app.call_from_thread(self._reset_download_state)
                    else:
                        # Direct assignment as fallback
                        self.is_downloading = False
                        self.download_thread = None
                except Exception:
                    # App context is gone (NoActiveAppError)
                    # Direct assignment as fallback
                    self.is_downloading = False
                    self.download_thread = None
            except Exception as e:
                # Fallback: try direct assignment
                try:
                    self.is_downloading = False
                    self.download_thread = None
                except Exception as e2:
                    pass  # Silently handle final fallback error

    def _update_status(self, status: str) -> None:
        """Update status from worker thread."""
        # Check if app is still running before trying to update
        try:
            if not hasattr(self, 'app') or not self.app.is_running:
                return
        except Exception:
            # App context is gone (NoActiveAppError)
            return
            
        try:
            self.app.call_from_thread(lambda: setattr(self, 'status', status))
        except Exception as e:
            # Don't try fallback assignment if app is not running
            if any(phrase in str(e).lower() for phrase in ["not running", "no active app", "no screen"]):
                return

    def _reset_download_state(self) -> None:
        """Reset download state on main thread."""
        self.is_downloading = False
        self.download_thread = None
        
        # Unmount progress bar if it exists
        # try:
        #     progress_bar = self.query_one("#progress-bar", None)
        #     if progress_bar:
        #         progress_bar.remove()
        # except Exception:
        #     # Progress bar might not exist
        #     pass

    def _on_progress_update(self, progress: DownloadProgress) -> None:
        """Handle progress updates from the downloader."""
        print(f"[DEBUG] Progress update received: {progress.overall_percentage}% - {progress.status}")
        
        # Check if app is still running before trying to update UI
        try:
            if not hasattr(self, 'app') or not self.app.is_running:
                print(f"[DEBUG] App not running, skipping progress update")
                return
        except Exception:
            # App context is gone (NoActiveAppError)
            print(f"[DEBUG] App context gone, skipping progress update")
            return
            
        try:
            # Update UI on main thread
            self.app.call_from_thread(self._update_progress_ui, progress)
        except Exception as e:
            print(f"[DEBUG] Error calling from thread: {e}")
            if any(phrase in str(e).lower() for phrase in ["not running", "no active app", "no screen"]):
                return
    
    def _update_progress_ui(self, progress: DownloadProgress) -> None:
        """Update progress UI on main thread."""
        self.progress = progress.overall_percentage / 100.0
        self.status = progress.status.title()
        self.files_downloaded = progress.completed_files
        self.error_files = progress.error_files
        self.total_files = progress.total_files

        # Update the progress bar widget if it exists
        try:
            progress_bar = self.query_one("#progress-bar", None)
            if progress_bar:
                # Update progress bar with the percentage value
                progress_bar.update(progress=progress.overall_percentage)
                print(f"[DEBUG] Updated progress bar to {progress.overall_percentage}% (total files: {progress.total_files})")
            else:
                print(f"[DEBUG] Progress bar not found")
        except Exception as e:
            # Progress bar might not exist yet or might have been removed
            print(f"[DEBUG] Error updating progress bar: {e}")
            try:
                self.app.notify(f"Error updating progress bar: {e}")
            except Exception:
                pass


    def _on_file_completed(self, result: DownloadResult) -> None:
        """Handle file completed from the downloader."""
        pass  # We don't need to do anything special for individual files

    def _on_error(self, error: str) -> None:
        """Handle error from the downloader."""
        self._update_status(f"Error: {error}")
    
