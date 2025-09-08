"""Example Textual GUI integration with ProjectDownloader."""

import pathlib
from typing import Optional
from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Button, Header, Footer, ProgressBar, Static, Label
from project_downloader import ProjectDownloader, DownloadProgress, DownloadResult


class DownloadApp(App):
    """Example Textual app using ProjectDownloader."""

    CSS = """
    Screen {
        layout: vertical;
    }
    
    .download-container {
        layout: vertical;
        height: 100%;
        padding: 1;
    }
    
    .progress-section {
        layout: vertical;
        height: 20%;
        border: solid $primary;
        margin: 1;
        padding: 1;
    }
    
    .file-list {
        height: 60%;
        border: solid $primary;
        margin: 1;
        padding: 1;
    }
    
    .controls {
        layout: horizontal;
        height: 20%;
        border: solid $primary;
        margin: 1;
        padding: 1;
    }
    """

    def __init__(self, project_id: str, destination: Optional[pathlib.Path] = None):
        super().__init__()
        self.project_id = project_id
        self.destination = destination
        self.downloader: Optional[ProjectDownloader] = None
        self.is_downloading = False

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()

        with Container(classes="download-container"):
            with Container(classes="progress-section"):
                yield Label("Download Progress", id="progress-title")
                yield ProgressBar(id="progress-bar")
                yield Label("0%", id="percentage-label")
                yield Label("Ready", id="status-label")
                yield Label("", id="current-file-label")

            with Container(classes="file-list"):
                yield Label("Files to Download:", id="file-list-title")
                yield Static("", id="file-list-content")

            with Container(classes="controls"):
                yield Button("Initialize", id="init-btn", variant="primary")
                yield Button("Download All", id="download-all-btn", disabled=True)
                yield Button("Cancel", id="cancel-btn", disabled=True, variant="error")

        yield Footer()

    def on_mount(self) -> None:
        """Called when app starts."""
        self.title = f"DDS Downloader - {self.project_id}"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "init-btn":
            self.initialize_downloader()
        elif event.button.id == "download-all-btn":
            self.start_download()
        elif event.button.id == "cancel-btn":
            self.cancel_download()

    def initialize_downloader(self) -> None:
        """Initialize the downloader."""
        try:
            self.downloader = ProjectDownloader(
                project=self.project_id, destination=self.destination
            )

            # Set up callbacks
            self.downloader.set_progress_callback(self.on_progress_update)
            self.downloader.set_file_completed_callback(self.on_file_completed)
            self.downloader.set_error_callback(self.on_error)

            # Initialize with all files
            if self.downloader.initialize(get_all=True):
                self.query_one("#init-btn").disabled = True
                self.query_one("#download-all-btn").disabled = False
                self.query_one("#status-label").update("Ready to download")

                # Update file list
                files = self.downloader.get_file_list()
                file_list_text = "\n".join(
                    f"• {file}" for file in files[:10]
                )  # Show first 10 files
                if len(files) > 10:
                    file_list_text += f"\n... and {len(files) - 10} more files"
                self.query_one("#file-list-content").update(file_list_text)
            else:
                self.query_one("#status-label").update("Initialization failed")

        except (ValueError, OSError, RuntimeError) as e:
            self.query_one("#status-label").update(f"Error: {str(e)}")

    def start_download(self) -> None:
        """Start the download process."""
        if not self.downloader or self.is_downloading:
            return

        self.is_downloading = True
        self.query_one("#download-all-btn").disabled = True
        self.query_one("#cancel-btn").disabled = False
        self.query_one("#status-label").update("Starting download...")

        # Start download in a worker thread
        self.run_worker(self._download_worker(), name="download")

    def cancel_download(self) -> None:
        """Cancel the download."""
        if self.downloader and self.is_downloading:
            self.downloader.cancel_download()
            self.is_downloading = False
            self.query_one("#download-all-btn").disabled = False
            self.query_one("#cancel-btn").disabled = True
            self.query_one("#status-label").update("Download cancelled")

    async def _download_worker(self) -> None:
        """Worker function for downloading."""
        try:
            if self.downloader:
                success = self.downloader.download_all(num_threads=4)

                # Update UI based on result
                if success:
                    self.query_one("#status-label").update("Download completed successfully!")
                else:
                    self.query_one("#status-label").update("Download failed or was cancelled")

                self.query_one("#download-all-btn").disabled = False
                self.query_one("#cancel-btn").disabled = True
                self.is_downloading = False

        except (ValueError, OSError, RuntimeError) as e:
            self.query_one("#status-label").update(f"Download error: {str(e)}")
            self.query_one("#download-all-btn").disabled = False
            self.query_one("#cancel-btn").disabled = True
            self.is_downloading = False

    def on_progress_update(self, progress: DownloadProgress) -> None:
        """Handle progress updates from the downloader."""
        # Update progress bar (0.0 to 1.0)
        self.query_one("#progress-bar").update(progress=progress.overall_progress)

        # Update percentage label
        self.query_one("#percentage-label").update(f"{progress.overall_percentage:.1f}%")

        # Update status
        self.query_one("#status-label").update(progress.status)

        # Update current file
        if progress.current_file:
            self.query_one("#current-file-label").update(f"Current: {progress.current_file}")
        else:
            self.query_one("#current-file-label").update("")

    def on_file_completed(self, result: DownloadResult) -> None:
        """Handle individual file completion."""
        if result.success:
            # Could add to a success list or update counters
            pass
        else:
            # Could add to an error list or show error dialog
            self.query_one("#status-label").update(f"Error downloading {result.file_path}")

    def on_error(self, error_message: str) -> None:
        """Handle errors from the downloader."""
        self.query_one("#status-label").update(f"Error: {error_message}")

    async def action_quit(self) -> None:
        """Quit the application."""
        if self.downloader:
            self.downloader.cleanup()
        self.exit()


def main():
    """Run the example app."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python textual_example.py <project-id> [destination]")
        sys.exit(1)

    project_id = sys.argv[1]
    destination = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else None

    app = DownloadApp(project_id, destination)
    app.run()


if __name__ == "__main__":
    main()
