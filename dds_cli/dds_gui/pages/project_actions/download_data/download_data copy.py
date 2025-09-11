"""DDS Download Data Widget"""

import logging
import pathlib
import threading
from typing import Any, Optional
from textual import events
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import ProgressBar
from textual.timer import Timer

from dds_cli.dds_gui.components.dds_container import DDSSpacedContainer
from dds_cli.dds_gui.components.dds_button import DDSButton
from dds_cli.dds_gui.utils.project_downloader import ProjectDownloader

# from dds_cli.dds_gui.utils.project_downloader import DownloadProgress, DownloadResult

LOG = logging.getLogger(__name__)


class DownloadData(Widget):
    """A widget for downloading data."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._downloader: Optional[ProjectDownloader] = None
        self._download_thread: Optional[threading.Thread] = None
        self._is_downloading = False
        self._download_destination: Optional[pathlib.Path] = None

    progress_timer: Timer

    DEFAULT_CSS = """
    DownloadData {
        height: auto;
        width: 100%;
    }

    #download-progress-container {
        margin: 1 0;
    }

    #progress-bar {
        margin: 0 0 1 0;
    }

    #status-label {
        text-align: center;
        margin: 0 0 1 0;
    }

    #current-file-label {
        text-align: center;
        color: $text-muted;
        margin: 0 0 1 0;
    }

    #percentage-label {
        text-align: center;
        color: $text-muted;
        margin: 0 0 1 0;
    }

    #error-label {
        color: $error;
        text-align: center;
        margin: 1 0;
    }

    #success-label {
        color: $success;
        text-align: center;
        margin: 1 0;
    }

    #cancel-button {
        margin: 1 0 0 0;
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
            self._mount_progress_bar()
            self._start_download()
        elif event.button.id == "cancel-download-button":
            self._cancel_download()

    def _mount_progress_bar(self) -> None:
        """Mount the progress bar."""
        container = self.query_one("#download-data-container")
        container.mount(ProgressBar(show_eta=False, id="progress-bar"))
        self.query_one(ProgressBar).update(total=100)  # Set total progress to 100%

    def _start_download(self) -> None:
        """Start the download process."""
        print("DEBUG: _start_download() called")

        if self._is_downloading:
            self.app.notify("Download already in progress", severity="warning")
            print("DEBUG: Download already in progress")
            return

        if not self.app.selected_project_id:
            self.app.notify("No project selected", severity="error")
            self._show_error("No project selected")
            print("DEBUG: No project selected")
            return

        LOG.info("Selected project ID: %s", self.app.selected_project_id)
        self.app.notify(f"Selected project: {self.app.selected_project_id}", severity="information")
        print(f"DEBUG: Selected project ID: {self.app.selected_project_id}")

        # Validate project ID format
        if not self.app.selected_project_id or not isinstance(self.app.selected_project_id, str):
            self.app.notify("Invalid project ID format", severity="error")
            self._show_error("Invalid project ID format")
            print("DEBUG: Invalid project ID format")
            return

        if not self.app.selected_project_id.startswith("datacentre"):
            self.app.notify("Project ID must start with 'datacentre'", severity="error")
            self._show_error("Project ID must start with 'datacentre'")
            print("DEBUG: Project ID doesn't start with 'datacentre'")
            return

        try:
            # Set up download destination
            self._download_destination = (
                pathlib.Path.home() / "Downloads" / f"dds_project_{self.app.selected_project_id}"
            )
            self._download_destination.mkdir(parents=True, exist_ok=True)

            # Initialize downloader
            self._downloader = ProjectDownloader(
                project=self.app.selected_project_id,
                destination=self._download_destination,
            )

            # Comment out callbacks for now to simplify
            # self._downloader.set_progress_callback(self._on_progress_update)
            # self._downloader.set_file_completed_callback(self._on_download_complete)
            # self._downloader.set_error_callback(self._on_download_error)

            # Show progress UI
            # self._show_progress_ui()

            # Notify start of download
            self.app.notify(
                f"Starting download to {self._download_destination}", severity="information"
            )

            # Start download in background thread after a short delay to ensure UI is mounted
            self._is_downloading = True
            self._download_thread = threading.Thread(target=self._run_download, daemon=True)
            print(
                f"DEBUG: About to start download thread for project: {self.app.selected_project_id}"
            )
            self._download_thread.start()
            print("DEBUG: Download thread started")

            # Check if thread is alive after a short delay
            import time

            time.sleep(0.1)
            print(f"DEBUG: Thread alive after start: {self._download_thread.is_alive()}")
            print("DEBUG: _start_download() completed successfully")

        except (OSError, ValueError, RuntimeError) as e:
            LOG.error("Failed to start download: %s", e)
            self.app.notify(f"Failed to start download: {str(e)}", severity="error")
            self._show_error(f"Failed to start download: {str(e)}")
            print(f"DEBUG: Exception in _start_download: {e}")
        except Exception as e:
            LOG.error("Unexpected error during download setup: %s", e)
            self.app.notify(f"Unexpected error: {str(e)}", severity="error")
            self._show_error(f"Unexpected error: {str(e)}")
            print(f"DEBUG: Unexpected exception in _start_download: {e}")
            import traceback

            traceback.print_exc()

    def _run_download(self) -> None:
        """Run the download in a background thread."""
        try:
            LOG.info("Starting download thread")
            self.app.notify("Download thread started", severity="information")
            print(f"DEBUG: Download thread started for project: {self.app.selected_project_id}")

            LOG.info("Initializing downloader...")
            self.app.notify("Initializing downloader...", severity="information")
            print("DEBUG: About to call downloader.initialize()")

            init_result = self._downloader.initialize(get_all=True)
            print(f"DEBUG: Initialize result: {init_result}")

            if init_result:
                LOG.info("Downloader initialized successfully")
                self.app.notify("Downloader initialized successfully", severity="information")
                print("DEBUG: Downloader initialized successfully")

                # Check if we have files to download
                getter = getattr(self._downloader, "_getter", None)
                print(f"DEBUG: Getter exists: {getter is not None}")

                if getter and hasattr(getter, "filehandler"):
                    file_count = len(getter.filehandler.data) if getter.filehandler.data else 0
                    LOG.info("Found %d files to download", file_count)
                    self.app.notify(f"Found {file_count} files to download", severity="information")
                    print(f"DEBUG: Found {file_count} files to download")

                    if file_count == 0:
                        LOG.error("No files found to download")
                        self.app.notify("No files found to download", severity="error")
                        print("DEBUG: No files found to download")
                        self._is_downloading = False
                        return
                else:
                    LOG.error("File handler not available")
                    self.app.notify("File handler not available", severity="error")
                    print("DEBUG: File handler not available")
                    self._is_downloading = False
                    return

                LOG.info("Starting file download...")
                self.app.notify("Starting file download...", severity="information")
                print("DEBUG: About to start download_all()")

                with self._downloader:
                    print("DEBUG: Inside context manager, calling download_all()")
                    self._downloader.download_all()
                    print("DEBUG: download_all() completed")

                LOG.info("Download completed successfully")
                self.app.notify("Download completed successfully!", severity="information")
                print("DEBUG: Download completed successfully")
            else:
                LOG.error("Failed to initialize downloader")
                self.app.notify("Failed to initialize downloader", severity="error")
                print("DEBUG: Failed to initialize downloader")

        except Exception as e:
            LOG.error("Download failed: %s", e)
            self.app.notify(f"Download failed: {e}", severity="error")
            print(f"DEBUG: Exception in download thread: {e}")
            import traceback

            traceback.print_exc()
        finally:
            self._is_downloading = False
            print("DEBUG: Download thread finished, _is_downloading set to False")

    def _cancel_download(self) -> None:
        """Cancel the current download."""
        if self._downloader and self._is_downloading:
            self._downloader.cancel_download()
            self._is_downloading = False
            self.app.notify("Download cancelled", severity="information")
            self._show_message("Download cancelled", is_error=False)
        else:
            self.app.notify("No active download to cancel", severity="warning")

    # def _show_progress_ui(self) -> None:
    #     """Show the progress UI elements."""
    #     container = self.query_one("#download-data-container")

    #     # Remove existing progress elements
    #     for widget in container.query("#download-progress-container, #error-label, #success-label"):
    #         widget.remove()

    #     # Add progress container
    #     with container:
    #         with DDSSpacedContainer(id="download-progress-container"):
    #             yield Label("Preparing download...", id="status-label")
    #             yield ProgressBar(show_eta=False, id="progress-bar")
    #             yield Label("", id="current-file-label")
    #             yield Label("0%", id="percentage-label")
    #             yield DDSButton("Cancel Download", id="cancel-download-button")

    #     # Disable the main download button
    #     self.query_one("#download-project-content-button").disabled = True

    def _show_error(self, message: str) -> None:
        """Show an error message."""
        # self._clear_messages()
        # container = self.query_one("#download-data-container")
        # with container:
        # yield Label(message, id="error-label")
        self.app.notify(message, severity="error")

    def _show_message(self, message: str, is_error: bool = False) -> None:
        """Show a success or error message."""
        # self._clear_messages()
        # container = self.query_one("#download-data-container")
        # with container:
        #     #yield Label(message, id="success-label" if not is_error else "error-label")
        self.app.notify(message, severity="information" if not is_error else "error")

    # def _clear_messages(self) -> None:
    #     """Clear existing error/success messages."""
    #     for widget in self.query("#error-label, #success-label"):
    #         widget.remove()

    # Comment out progress update for now
    # def _on_progress_update(self, progress: DownloadProgress) -> None:
    #     """Handle progress updates from the downloader."""
    #     pass

    # Comment out download complete for now
    # def _on_download_complete(self, result: DownloadResult) -> None:
    #     """Handle download completion."""
    #     pass

    # Comment out download error for now
    # def _on_download_error(self, error_message: str) -> None:
    #     """Handle download errors."""
    #     pass
