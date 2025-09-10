"""DDS Download Data Widget"""

import logging
import pathlib
import threading
from typing import Any, Optional
from textual import events
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Label, ProgressBar
from textual.timer import Timer

from dds_cli.dds_gui.components.dds_container import DDSSpacedContainer
from dds_cli.dds_gui.components.dds_button import DDSButton
from dds_cli.dds_gui.utils.project_downloader import (
    ProjectDownloader,
    DownloadProgress,
    DownloadResult,
)

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
            #self._start_download()
        elif event.button.id == "cancel-download-button":
            self._cancel_download()

    def _mount_progress_bar(self) -> None:
        """Mount the progress bar."""
        container = self.query_one("#download-data-container")
        container.mount(ProgressBar(show_eta=False, id="progress-bar"))

    def _start_download(self) -> None:
        """Start the download process."""
        if self._is_downloading:
            self.app.notify("Download already in progress", severity="warning")
            return

        if not self.app.selected_project_id:
            self.app.notify("No project selected", severity="error")
            self._show_error("No project selected")
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

            # Set up callbacks
            self._downloader.set_progress_callback(self._on_progress_update)
            self._downloader.set_file_completed_callback(self._on_download_complete)
            self._downloader.set_error_callback(self._on_download_error)

            # Show progress UI
            self._show_progress_ui()

            # Notify start of download
            self.app.notify(
                f"Starting download to {self._download_destination}", severity="information"
            )

            # Start download in background thread after a short delay to ensure UI is mounted
            self._is_downloading = True
            self._download_thread = threading.Thread(target=self._run_download, daemon=True)
            self._download_thread.start()

        except (OSError, ValueError, RuntimeError) as e:
            self.app.notify(f"Failed to start download: {str(e)}", severity="error")
            self._show_error(f"Failed to start download: {str(e)}")

    def _run_download(self) -> None:
        """Run the download in a background thread."""
        try:
            # Small delay to ensure UI is fully mounted
            import time

            time.sleep(0.1)

            with self._downloader:
                self._downloader.initialize(get_all=True)
                self._downloader.download_all()
        except (OSError, ValueError, RuntimeError) as e:
            self.app.notify(f"Download failed: {e}", severity="error")
            # Error will be handled by error callback

    def _cancel_download(self) -> None:
        """Cancel the current download."""
        if self._downloader and self._is_downloading:
            self._downloader.cancel_download()
            self._is_downloading = False
            self.app.notify("Download cancelled", severity="information")
            self._show_message("Download cancelled", is_error=False)
        else:
            self.app.notify("No active download to cancel", severity="warning")

    def _show_progress_ui(self) -> None:
        """Show the progress UI elements."""
        container = self.query_one("#download-data-container")

        # Remove existing progress elements
        for widget in container.query("#download-progress-container, #error-label, #success-label"):
            widget.remove()

        # Add progress container
        with container:
            with DDSSpacedContainer(id="download-progress-container"):
                yield Label("Preparing download...", id="status-label")
                yield ProgressBar(show_eta=False, id="progress-bar")
                yield Label("", id="current-file-label")
                yield Label("0%", id="percentage-label")
                yield DDSButton("Cancel Download", id="cancel-download-button")

        # Disable the main download button
        self.query_one("#download-project-content-button").disabled = True

    def _show_error(self, message: str) -> None:
        """Show an error message."""
        self._clear_messages()
        container = self.query_one("#download-data-container")
        with container:
            yield Label(message, id="error-label")

    def _show_message(self, message: str, is_error: bool = False) -> None:
        """Show a success or error message."""
        self._clear_messages()
        container = self.query_one("#download-data-container")
        with container:
            yield Label(message, id="success-label" if not is_error else "error-label")

    def _clear_messages(self) -> None:
        """Clear existing error/success messages."""
        for widget in self.query("#error-label, #success-label"):
            widget.remove()

    def _on_progress_update(self, progress: DownloadProgress) -> None:
        """Handle progress updates from the downloader."""

        def update_ui():
            try:
                # Check if progress UI elements exist before updating
                if not self.query("#progress-bar"):
                    self.app.notify("Progress bar not found, skipping update", severity="information")
                    return

                # Update progress bar
                progress_bar = self.query_one("#progress-bar", expect_type=ProgressBar)
                progress_bar.update(progress=progress.overall_progress)

                # Update status
                if self.query("#status-label"):
                    status_label = self.query_one("#status-label", expect_type=Label)
                    status_label.update(progress.status.title())

                # Update current file
                if self.query("#current-file-label"):
                    current_file_label = self.query_one("#current-file-label", expect_type=Label)
                    if progress.current_file:
                        current_file_label.update(f"Current: {progress.current_file}")
                    else:
                        current_file_label.update("")

                # Update percentage
                if self.query("#percentage-label"):
                    percentage_label = self.query_one("#percentage-label", expect_type=Label)
                    percentage_label.update(f"{progress.overall_percentage:.1f}%")

                # Notify on significant progress milestones
                if progress.overall_percentage > 0 and progress.overall_percentage % 25 == 0:
                    self.app.notify(
                        f"Download progress: {progress.overall_percentage:.0f}% complete",
                        severity="information",
                    )

            except (AttributeError, ValueError) as e:
                self.app.notify(f"Failed to update progress UI: {e}", severity="error")

        # Schedule UI update on main thread
        self.call_after_refresh(update_ui)

    def _on_download_complete(self, result: DownloadResult) -> None:
        """Handle download completion."""

        def complete_ui():
            try:
                # Remove progress UI if it exists
                if self.query("#download-progress-container"):
                    progress_container = self.query_one("#download-progress-container")
                    progress_container.remove()

                # Re-enable download button
                if self.query("#download-project-content-button"):
                    self.query_one("#download-project-content-button").disabled = False

                # Show success message and notify
                if result.success:
                    self.app.notify(
                        f"Download completed! {result.files_downloaded} files downloaded to {self._download_destination}",
                        severity="information",
                    )
                    self._show_message(
                        f"Download completed successfully!\n"
                        f"Files downloaded: {result.files_downloaded}\n"
                        f"Destination: {self._download_destination}"
                    )
                else:
                    self.app.notify(f"Download failed: {result.error_message}", severity="error")
                    self._show_error(f"Download failed: {result.error_message}")

            except (AttributeError, ValueError) as e:
                self.app.notify(f"Failed to update completion UI: {e}", severity="error")

        self._is_downloading = False
        self.call_after_refresh(complete_ui)

    def _on_download_error(self, error_message: str) -> None:
        """Handle download errors."""

        def error_ui():
            try:
                # Remove progress UI if it exists
                if self.query("#download-progress-container"):
                    progress_container = self.query_one("#download-progress-container")
                    progress_container.remove()

                # Re-enable download button
                if self.query("#download-project-content-button"):
                    self.query_one("#download-project-content-button").disabled = False

                # Show error message and notify
                self.app.notify(f"Download failed: {error_message}", severity="error")
                self._show_error(f"Download failed: {error_message}")

            except (AttributeError, ValueError) as e:
                self.app.notify(f"Failed to update error UI: {e}", severity="error")

        self._is_downloading = False
        self.call_after_refresh(error_ui)
