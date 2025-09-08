"""Example usage of ProjectDownloader for GUI integration."""

import pathlib
from typing import Optional
from project_downloader import ProjectDownloader, DownloadProgress, DownloadResult


class GUIDownloadManager:
    """Example GUI download manager using ProjectDownloader."""

    def __init__(self, project_id: str, destination: Optional[pathlib.Path] = None):
        """Initialize the GUI download manager.

        Args:
            project_id: DDS project ID to download from
            destination: Optional destination directory
        """
        self.project_id = project_id
        self.destination = destination
        self.downloader: Optional[ProjectDownloader] = None
        self.is_downloading = False

    def start_download(
        self,
        get_all: bool = False,
        source_files: tuple = (),
        source_path_file: Optional[pathlib.Path] = None,
        num_threads: int = 4,
    ) -> bool:
        """Start a download operation.

        Args:
            get_all: Whether to download all project contents
            source_files: Specific files to download
            source_path_file: Path to file containing source list
            num_threads: Number of concurrent download threads

        Returns:
            True if download started successfully, False otherwise
        """
        if self.is_downloading:
            print("Download already in progress")
            return False

        try:
            # Create downloader instance
            self.downloader = ProjectDownloader(
                project=self.project_id, destination=self.destination
            )

            # Set up callbacks
            self.downloader.set_progress_callback(self._on_progress)
            self.downloader.set_file_completed_callback(self._on_file_completed)
            self.downloader.set_error_callback(self._on_error)

            # Initialize downloader
            if not self.downloader.initialize(
                get_all=get_all, source=source_files, source_path_file=source_path_file
            ):
                print("Failed to initialize downloader")
                return False

            # Start download in a separate thread (GUI should handle this)
            self.is_downloading = True
            download_success = self.downloader.download_all(num_threads=num_threads)
            self.is_downloading = False

            return download_success

        except (ValueError, OSError, RuntimeError) as e:
            print(f"Download failed: {e}")
            self.is_downloading = False
            return False

    def cancel_download(self) -> None:
        """Cancel the current download operation."""
        if self.downloader and self.is_downloading:
            self.downloader.cancel_download()
            self.is_downloading = False

    def get_file_list(self) -> list:
        """Get list of files available for download.

        Returns:
            List of file paths
        """
        if self.downloader:
            return self.downloader.get_file_list()
        return []

    def download_single_file(self, file_path: str) -> DownloadResult:
        """Download a single file.

        Args:
            file_path: Path to file to download

        Returns:
            DownloadResult with success status
        """
        if not self.downloader:
            return DownloadResult(
                success=False, file_path=file_path, error_message="Downloader not initialized"
            )

        return self.downloader.download_file(file_path)

    def _on_progress(self, progress: DownloadProgress) -> None:
        """Handle progress updates.

        Args:
            progress: Progress information
        """
        # Update GUI progress bar, status label, etc.
        print(f"Progress: {progress.overall_percentage:.1f}% - {progress.status}")
        if progress.current_file:
            print(f"Current file: {progress.current_file}")

        # Example Textual GUI updates:
        # self.progress_bar.update(progress=progress.overall_progress)
        # self.status_label.update(progress.status)
        # self.current_file_label.update(progress.current_file)
        # self.percentage_label.update(f"{progress.overall_percentage:.1f}%")

    def _on_file_completed(self, result: DownloadResult) -> None:
        """Handle file completion.

        Args:
            result: Download result information
        """
        if result.success:
            print(f"✓ Downloaded: {result.file_path}")
            # Update GUI: add to completed files list, update counters, etc.
        else:
            print(f"✗ Failed: {result.file_path} - {result.error_message}")
            # Update GUI: add to failed files list, show error dialog, etc.

    def _on_error(self, error_message: str) -> None:
        """Handle errors.

        Args:
            error_message: Error message
        """
        print(f"Error: {error_message}")
        # Update GUI: show error dialog, update status, etc.
        # self.error_dialog.showMessage(error_message)

    def cleanup(self) -> None:
        """Clean up resources."""
        if self.downloader:
            self.downloader.cleanup()
            self.downloader = None
        self.is_downloading = False


# Example usage
if __name__ == "__main__":
    # Create download manager
    manager = GUIDownloadManager(
        project_id="your-project-id", destination=pathlib.Path("./downloads")
    )

    # Download all files
    print("Starting download...")
    success = manager.start_download(get_all=True, num_threads=4)

    if success:
        print("Download completed successfully!")
    else:
        print("Download failed or was cancelled")

    # Clean up
    manager.cleanup()
