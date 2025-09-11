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
            if progress.bytes_downloaded > 0 and progress.total_bytes > 0:
                file_progress = (progress.bytes_downloaded / progress.total_bytes) * 100
                print(f"  File progress: {file_progress:.1f}% ({progress.bytes_downloaded}/{progress.total_bytes} bytes)")

        # Example Textual GUI updates with real-time progress:
        # self.progress_bar.update(progress=progress.overall_progress)
        # self.status_label.update(progress.status)
        # self.current_file_label.update(progress.current_file)
        # self.percentage_label.update(f"{progress.overall_percentage:.1f}%")
        # 
        # # Real-time file progress (new feature!)
        # if progress.bytes_downloaded > 0:
        #     self.file_progress_bar.update(progress=progress.current_file_progress)
        #     self.file_bytes_label.update(f"{progress.bytes_downloaded:,}/{progress.total_bytes:,} bytes")

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
        project_id="datacentre00358"
    )

    # Download all files with improved progress tracking
    print("Starting download with real-time progress updates...")
    print("=" * 60)
    
    success = manager.start_download(get_all=True, num_threads=4)

    print("=" * 60)
    if success:
        print("✅ Download completed successfully!")
    else:
        print("❌ Download failed or was cancelled")

    # Clean up
    manager.cleanup()


# Test with a larger file to see intermediate progress
def create_test_large_file():
    """Create a test file large enough to see intermediate progress."""
    import os
    test_file = "test_large_file.txt"
    
    # Create a 1MB file to see intermediate progress
    with open(test_file, "w") as f:
        for i in range(1000):  # 1000 lines of 1KB each
            f.write(f"Line {i:04d}: " + "x" * 1000 + "\n")
    
    print(f"Created test file: {test_file} ({os.path.getsize(test_file)} bytes)")
    return test_file


# Example with intermediate progress demonstration
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Testing intermediate progress updates...")
    print("=" * 60)
    
    # Create a test file to upload first (if you have upload capabilities)
    # For now, let's just test with the existing project
    print("Note: To see intermediate progress, you need a file larger than 64KB")
    print("The current test file (hello.txt) is only 65 bytes, so it downloads in one chunk")
    print("For intermediate progress, try with a larger file in the project")
    
    # Test with existing project
    test_manager = GUIDownloadManager(project_id="datacentre00358")
    test_manager.start_download(get_all=True, num_threads=1)  # Single thread to see progress clearly
    test_manager.cleanup()


# Advanced example showing detailed progress tracking
class AdvancedGUIDownloadManager(GUIDownloadManager):
    """Advanced GUI download manager with detailed progress tracking."""

    def __init__(self, project_id: str, destination: Optional[pathlib.Path] = None):
        super().__init__(project_id, destination)
        self.download_stats = {
            "total_files": 0,
            "completed_files": 0,
            "failed_files": 0,
            "total_bytes": 0,
            "downloaded_bytes": 0,
            "start_time": None,
        }

    def _on_progress(self, progress: DownloadProgress) -> None:
        """Handle detailed progress updates with statistics."""
        # Update statistics
        if progress.total_files > 0:
            self.download_stats["total_files"] = progress.total_files
        if progress.bytes_downloaded > 0:
            self.download_stats["downloaded_bytes"] = progress.bytes_downloaded
        if progress.total_bytes > 0:
            self.download_stats["total_bytes"] = progress.total_bytes

        # Calculate download speed (simplified)
        if self.download_stats["start_time"] is None:
            self.download_stats["start_time"] = time.time()
        
        elapsed_time = time.time() - self.download_stats["start_time"]
        if elapsed_time > 0 and progress.bytes_downloaded > 0:
            speed_mbps = (progress.bytes_downloaded / (1024 * 1024)) / elapsed_time
        else:
            speed_mbps = 0

        # Display detailed progress with better formatting
        if progress.current_file and progress.bytes_downloaded > 0:
            file_progress = progress.current_file_progress * 100
            print(f"\r📊 Progress: {progress.overall_percentage:.1f}% | "
                  f"Files: {progress.completed_files}/{progress.total_files} | "
                  f"Speed: {speed_mbps:.1f} MB/s | "
                  f"Status: {progress.status}")
            print(f"  📁 {progress.current_file}: {file_progress:.1f}% "
                  f"({progress.bytes_downloaded:,}/{progress.total_bytes:,} bytes)")
        else:
            print(f"\r📊 Progress: {progress.overall_percentage:.1f}% | "
                  f"Files: {progress.completed_files}/{progress.total_files} | "
                  f"Status: {progress.status}", end="", flush=True)

    def _on_file_completed(self, result: DownloadResult) -> None:
        """Handle file completion with statistics."""
        if result.success:
            self.download_stats["completed_files"] += 1
            print(f"\n✅ Downloaded: {result.file_path}")
        else:
            self.download_stats["failed_files"] += 1
            print(f"\n❌ Failed: {result.file_path} - {result.error_message}")

    def get_download_summary(self) -> dict:
        """Get download statistics summary."""
        return self.download_stats.copy()


# Example of advanced usage
if __name__ == "__main__":
    import time
    
    print("Advanced Download Example")
    print("=" * 60)
    
    # Create advanced download manager
    advanced_manager = AdvancedGUIDownloadManager(
        project_id="datacentre00137"
    )

    # Download with detailed tracking
    success = advanced_manager.start_download(get_all=True, num_threads=4)
    
    # Show summary
    summary = advanced_manager.get_download_summary()
    print(f"\n📈 Download Summary:")
    print(f"  Total files: {summary['total_files']}")
    print(f"  Completed: {summary['completed_files']}")
    print(f"  Failed: {summary['failed_files']}")
    print(f"  Total bytes: {summary['total_bytes']:,}")
    print(f"  Downloaded bytes: {summary['downloaded_bytes']:,}")
    
    advanced_manager.cleanup()
