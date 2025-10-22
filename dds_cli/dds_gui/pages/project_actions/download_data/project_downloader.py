"""Project downloader utility for GUI integration."""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import concurrent.futures
import itertools
import pathlib
import threading
import time
import logging
from typing import Callable, Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

# Own modules
import dds_cli
import dds_cli.data_getter
import dds_cli.directory
import dds_cli.exceptions
import dds_cli.utils

# Logger
LOG = logging.getLogger(__name__)

###############################################################################
# CLASSES ########################################################### CLASSES #
###############################################################################


@dataclass
class DownloadProgress:
    """Progress information for a download operation."""

    current_file: str
    total_files: int
    completed_files: int
    error_files: int
    current_file_progress: float  # 0.0 to 1.0
    overall_progress: float  # 0.0 to 1.0
    overall_percentage: float  # 0.0 to 100.0 for easy Textual integration
    status: str  # "preparing", "downloading", "decrypting", "completed", "error"
    error_message: Optional[str] = None
    bytes_downloaded: int = 0
    total_bytes: int = 0


@dataclass
class DownloadResult:
    """Result of a download operation."""

    success: bool
    file_path: str
    files_downloaded: int = 1
    error_message: Optional[str] = None
    file_size: Optional[int] = None


class CallbackProgress:
    """Progress class that triggers callbacks for real-time updates."""

    def __init__(
        self,
        progress_callback: Optional[Callable[[DownloadProgress], None]],
        file_path: str,
        total_size: int,
        downloader_instance: "ProjectDownloader",
    ):
        """Initialize callback progress tracker.

        Args:
            progress_callback: Function to call with progress updates
            file_path: Path of the file being downloaded
            total_size: Total size of the file in bytes
            downloader_instance: Reference to the downloader for thread-safe updates
        """
        self.progress_callback = progress_callback
        self.file_path = file_path
        self.total_size = total_size
        self.downloader_instance = downloader_instance
        self.tasks = {}
        self.completed = 0
        self._lock = threading.Lock()
        self._last_callback_time = 0
        self._callback_throttle = 0.1  # Minimum 100ms between callbacks for less frequent updates
        self._last_callback_progress = 0  # Track last reported progress percentage

    def add_task(self, description, total=None, _step=None, visible=True):
        """Add a progress task (Rich compatibility).

        Args:
            description: Task description
            total: Total progress value
            step: Step size (unused, kept for Rich compatibility)
            visible: Whether task is visible
        """
        with self._lock:
            task_id = len(self.tasks)
            self.tasks[task_id] = {
                "description": description,
                "total": total or self.total_size,
                "completed": 0,
                "visible": visible,
            }
            return task_id

    def update(self, task_id, advance=None, description=None):
        """Update progress and trigger callbacks."""
        with self._lock:
            if task_id in self.tasks:
                if advance:
                    self.tasks[task_id]["completed"] += advance
                    self.completed += advance

                    # Always trigger callback when advance is provided (chunk downloaded)
                    if self.progress_callback:
                        self._trigger_progress_callback()

                if description:
                    self.tasks[task_id]["description"] = description

    def reset(self, task_id, description=None, total=None):
        """Reset task progress."""
        with self._lock:
            if task_id in self.tasks:
                if description:
                    self.tasks[task_id]["description"] = description
                if total:
                    self.tasks[task_id]["total"] = total
                self.tasks[task_id]["completed"] = 0

    def remove_task(self, task_id):
        """Remove a task."""
        with self._lock:
            if task_id in self.tasks:
                del self.tasks[task_id]

    def _trigger_progress_callback(self):
        """Trigger progress callback with current state."""
        if not self.progress_callback:
            return

        # Check if download was cancelled
        if self.downloader_instance.cancelled or (
            self.downloader_instance.getter and self.downloader_instance.getter.stop_doing
        ):
            return

        # Calculate current file progress
        current_file_progress = self.completed / max(self.total_size, 1)
        current_percentage = int(current_file_progress * 20)  # 5% increments instead of 1%

        # Trigger callback if:
        # 1. Enough time has passed (throttling), OR
        # 2. Progress percentage has changed by at least 5%, OR
        # 3. This is the first update (0% progress), OR
        # 4. This is the final update (100% progress), OR
        # 5. For small files, trigger less frequently based on bytes downloaded
        current_time = time.time()
        time_elapsed = current_time - self._last_callback_time
        progress_changed = current_percentage != self._last_callback_progress

        # For small files (< 1MB), trigger callbacks less frequently
        bytes_since_last_callback = self.completed - (
            self._last_callback_progress * self.total_size / 100
        )
        small_file_frequent_updates = (
            self.total_size < 1024 * 1024 and bytes_since_last_callback >= 1024
        )  # 1KB instead of 64 bytes

        if (
            time_elapsed >= self._callback_throttle
            or progress_changed
            or current_percentage == 0
            or current_percentage == 100
            or small_file_frequent_updates
        ):

            self._last_callback_time = current_time
            self._last_callback_progress = current_percentage

            # Get overall progress from downloader
            with self.downloader_instance.progress_lock:
                # Calculate overall progress based on bytes downloaded vs total bytes
                total_downloaded_bytes = self.downloader_instance.total_downloaded_bytes
                total_bytes = self.downloader_instance.total_bytes

                if total_bytes > 0:
                    # Calculate overall progress based on bytes
                    # total_downloaded_bytes includes completed files
                    # Add current file progress to it
                    current_file_downloaded = self.completed
                    overall_downloaded = total_downloaded_bytes + current_file_downloaded
                    overall_progress = min(overall_downloaded / total_bytes, 1.0)  # Cap at 100%
                    overall_percentage = overall_progress * 100.0
                else:
                    # Fallback to file-based progress if total bytes not available
                    completed_files = self.downloader_instance.completed_files
                    total_files = self.downloader_instance.total_files

                    if total_files == 1:
                        overall_progress = current_file_progress
                        overall_percentage = current_file_progress * 100.0
                    else:
                        base_progress = completed_files / max(total_files, 1)
                        current_file_contribution = current_file_progress / max(total_files, 1)
                        overall_progress = base_progress + current_file_contribution
                        overall_percentage = overall_progress * 100.0

            progress_info = DownloadProgress(
                current_file=self.file_path,
                total_files=self.downloader_instance.total_files,
                completed_files=self.downloader_instance.completed_files,
                error_files=self.downloader_instance.error_files,
                current_file_progress=current_file_progress,
                overall_progress=overall_progress,
                overall_percentage=overall_percentage,
                status="downloading",
                error_message=None,
                bytes_downloaded=self.completed,
                total_bytes=self.total_size,
            )

            # Use thread-safe callback execution
            self.downloader_instance.safe_callback_execution(
                lambda: self.progress_callback(progress_info)
            )


class ProjectDownloader:
    """GUI-friendly project downloader class.

    This class provides a modular interface for downloading project data
    that can be easily integrated with GUI applications. It supports:
    - Progress callbacks for real-time updates
    - Error handling and reporting
    - Concurrent downloads with configurable threading
    - Individual file or batch downloads
    - Cancellation support

    """

    def __init__(
        self,
        project: str,
        destination: Optional[pathlib.Path] = None,
        token_path: Optional[str] = None,
        no_prompt: bool = True,
    ):
        """Initialize the project downloader.

        Args:
            project: Project ID to download from
            destination: Optional destination directory (defaults to current directory)
            token_path: Optional path to authentication token
            no_prompt: Whether to skip user prompts (default True for GUI)
        """
        self.project = project
        self.destination = destination
        self.token_path = token_path
        self.no_prompt = no_prompt

        # Internal state
        self._getter: Optional[dds_cli.data_getter.DataGetter] = None
        self._staging_dir: Optional[dds_cli.directory.DDSDirectory] = None
        self._is_initialized = False
        self._is_downloading = False
        self._cancelled = False

        # Callbacks
        self._progress_callback: Optional[Callable[[DownloadProgress], None]] = None
        self._file_completed_callback: Optional[Callable[[DownloadResult], None]] = None
        self._error_callback: Optional[Callable[[str], None]] = None

        # Threading
        self._executor: Optional[concurrent.futures.ThreadPoolExecutor] = None
        self._download_threads: Dict[concurrent.futures.Future, str] = {}

        # Progress tracking
        self._progress_lock = threading.Lock()
        self._completed_files = 0
        self._error_files = 0
        self._total_files = 0
        self._total_bytes = 0
        self._total_downloaded_bytes = 0

        # Thread-safe callback execution
        self._callback_lock = threading.Lock()

    # Public properties for CallbackProgress access
    @property
    def cancelled(self) -> bool:
        """Get cancellation status."""
        return self._cancelled

    @property
    def getter(self) -> Optional[dds_cli.data_getter.DataGetter]:
        """Get the data getter instance."""
        return self._getter

    @property
    def progress_lock(self) -> threading.Lock:
        """Get the progress lock."""
        return self._progress_lock

    @property
    def total_downloaded_bytes(self) -> int:
        """Get total downloaded bytes."""
        return self._total_downloaded_bytes

    @property
    def total_bytes(self) -> int:
        """Get total bytes."""
        return self._total_bytes

    @property
    def completed_files(self) -> int:
        """Get completed files count."""
        return self._completed_files

    @property
    def total_files(self) -> int:
        """Get total files count."""
        return self._total_files

    @property
    def error_files(self) -> int:
        """Get error files count."""
        return self._error_files

    def safe_callback_execution(self, callback_func: Callable[[], None]) -> None:
        """Execute callback in a thread-safe manner.

        Args:
            callback_func: Function to execute safely
        """
        try:
            with self._callback_lock:
                callback_func()
        except (dds_cli.exceptions.ApiRequestError, dds_cli.exceptions.DownloadError) as error:
            LOG.warning("Callback execution failed due to DDS error: %s", error)
        except OSError as error:
            LOG.warning("Callback execution failed due to OS error: %s", error)
        except Exception as error:  # pylint: disable=broad-exception-caught
            # Don't log warnings for app shutdown errors as they're expected during shutdown
            error_msg = str(error).lower()
            if not any(
                phrase in error_msg
                for phrase in ["not running", "no active app", "no screen", "event loop is closed"]
            ):
                LOG.warning("Unexpected error in callback execution: %s", error)

    def set_progress_callback(self, callback: Callable[[DownloadProgress], None]) -> None:
        """Set callback for progress updates.

        Args:
            callback: Function to call with progress updates
        """
        self._progress_callback = callback

    def set_file_completed_callback(self, callback: Callable[[DownloadResult], None]) -> None:
        """Set callback for when individual files complete.

        Args:
            callback: Function to call when a file download completes
        """
        self._file_completed_callback = callback

    def set_error_callback(self, callback: Callable[[str], None]) -> None:
        """Set callback for error reporting.

        Args:
            callback: Function to call when errors occur
        """
        self._error_callback = callback

    def initialize(
        self,
        get_all: bool = False,
        source: Tuple = (),
        source_path_file: Optional[pathlib.Path] = None,
        break_on_fail: bool = False,
        verify_checksum: bool = False,
    ) -> bool:
        """Initialize the downloader with project data.

        Args:
            get_all: Whether to download all project contents
            source: Specific files/folders to download
            source_path_file: Path to file containing source list
            break_on_fail: Whether to stop on first failure
            verify_checksum: Whether to verify file checksums

        Returns:
            True if initialization successful, False otherwise
        """
        try:
            self._update_progress("preparing", "Initializing download...")

            # Validate parameters
            if get_all and (source or source_path_file):
                self._report_error("Cannot use 'get_all' with specific sources")
                return False
            if not get_all and not (source or source_path_file):
                self._report_error("Must specify sources or use 'get_all'")
                return False

            # Setup staging directory
            if self.destination:
                staging_dir_path = self.destination
            else:
                staging_dir_path = pathlib.Path.cwd() / pathlib.Path(
                    f"DataDelivery_{dds_cli.timestamp.TimeStamp().timestamp}_"
                    f"{self.project}_download"
                )

            self._staging_dir = dds_cli.directory.DDSDirectory(path=staging_dir_path)

            # Initialize data getter
            self._getter = dds_cli.data_getter.DataGetter(
                project=self.project,
                get_all=get_all,
                source=source,
                source_path_file=source_path_file,
                break_on_fail=break_on_fail,
                silent=True,  # GUI handles output
                verify_checksum=verify_checksum,
                no_prompt=self.no_prompt,
                token_path=self.token_path,
                staging_dir=self._staging_dir,
            )

            # Check if we have files to download
            if not self._getter.filehandler.data:
                self._report_error("No files to download")
                return False

            self._total_files = len(self._getter.filehandler.data)
            self._completed_files = 0

            # Calculate total bytes for all files
            self._total_bytes = sum(
                file_info["size_stored"] for file_info in self._getter.filehandler.data.values()
            )
            self._total_downloaded_bytes = 0

            self._is_initialized = True

            self._update_progress("preparing", f"Found {self._total_files} files to download")
            return True

        except (
            dds_cli.exceptions.InvalidMethodError,
            dds_cli.exceptions.TokenNotFoundError,
            dds_cli.exceptions.AuthenticationError,
            dds_cli.exceptions.ApiRequestError,
            dds_cli.exceptions.DownloadError,
            OSError,
            ValueError,
        ) as error:
            LOG.error("Initialization failed: %s", str(error))
            self._report_error(f"Initialization failed: {str(error)}")
            return False
        except Exception as error:  # pylint: disable=broad-exception-caught
            LOG.error("Unexpected error during initialization: %s", str(error))
            self._report_error(f"Unexpected initialization error: {str(error)}")
            return False

    def download_all(self, num_threads: int = 4) -> bool:
        """Download all files with concurrent threading.

        Args:
            num_threads: Number of concurrent download threads

        Returns:
            True if all downloads successful, False otherwise
        """
        if not self._is_initialized:
            self._report_error("Downloader not initialized")
            return False

        if self._is_downloading:
            self._report_error("Download already in progress")
            return False

        self._is_downloading = True
        self._cancelled = False

        # Check if we should stop before starting
        if self._getter and self._getter.stop_doing:
            self._is_downloading = False
            return False

        # Send initial progress update
        self._update_download_progress("preparing")

        try:
            # Create thread pool
            with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
                self._executor = executor

                # Iterator for files
                file_iterator = iter(self._getter.filehandler.data.copy())

                # Schedule initial batch of downloads
                for file in itertools.islice(file_iterator, num_threads):
                    if self._cancelled or self._getter.stop_doing:
                        break
                    self._schedule_download(file)

                # Update status to downloading when first files are scheduled
                if self._download_threads:
                    self._update_download_progress("downloading")

                # Process completed downloads and schedule new ones
                while (
                    self._download_threads and not self._cancelled and not self._getter.stop_doing
                ):
                    # Wait for next completion with timeout for more responsive cancellation
                    try:
                        done, _ = concurrent.futures.wait(
                            self._download_threads,
                            return_when=concurrent.futures.FIRST_COMPLETED,
                            timeout=0.1,  # 100ms timeout for responsive cancellation
                        )
                    except concurrent.futures.TimeoutError:
                        # Timeout occurred, check for cancellation and continue
                        if self._cancelled or self._getter.stop_doing:
                            break
                        continue

                    new_tasks = 0

                    for future in done:
                        # Check if future was cancelled
                        if future.cancelled():
                            continue

                        # Check if we should stop due to cancellation
                        if self._cancelled or self._getter.stop_doing:
                            break

                        file_path = self._download_threads.pop(future)

                        try:
                            result = future.result()

                            if isinstance(result, tuple) and len(result) == 2:
                                success, message = result
                            else:
                                # Handle case where result is not a tuple
                                # (DataGetter returns boolean)
                                success = bool(result)
                                message = "Download completed" if success else "Download failed"

                            if success:
                                self._completed_files += 1
                                # Update total downloaded bytes
                                file_size = self._getter.filehandler.data[file_path]["size_stored"]
                                self._total_downloaded_bytes += file_size
                            else:
                                self._error_files += 1

                            # Update progress with final file completion
                            self._update_download_progress(file_path)

                            # Trigger final progress callback for this file
                            if self._progress_callback:
                                final_progress = DownloadProgress(
                                    current_file=file_path,
                                    total_files=self._total_files,
                                    completed_files=self._completed_files,
                                    error_files=self._error_files,
                                    current_file_progress=1.0,  # File is complete
                                    overall_progress=(self._completed_files + self._error_files)
                                    / max(self._total_files, 1),
                                    overall_percentage=(
                                        (self._completed_files + self._error_files)
                                        / max(self._total_files, 1)
                                    )
                                    * 100.0,
                                    status="completed" if success else "error",
                                    error_message=message if not success else None,
                                    bytes_downloaded=(
                                        self._getter.filehandler.data[file_path]["size_stored"]
                                        if success
                                        else 0
                                    ),
                                    total_bytes=self._getter.filehandler.data[file_path][
                                        "size_stored"
                                    ],
                                )
                                self.safe_callback_execution(
                                    lambda progress=final_progress: self._progress_callback(
                                        progress
                                    )
                                )

                            # Create result object
                            download_result = DownloadResult(
                                success=success,
                                file_path=str(file_path),
                                error_message=message if not success else None,
                            )

                            # Notify callbacks
                            if self._file_completed_callback:
                                self.safe_callback_execution(
                                    lambda result=download_result: self._file_completed_callback(
                                        result
                                    )
                                )

                            # Download completed (success or failure)

                            new_tasks += 1

                        except (
                            dds_cli.exceptions.DownloadError,
                            dds_cli.exceptions.ApiRequestError,
                            OSError,
                            RuntimeError,
                        ) as error:
                            LOG.error("Download error for file %s: %s", file_path, str(error))
                            self._report_error(f"Download error: {str(error)}")
                        except Exception as error:  # pylint: disable=broad-exception-caught
                            LOG.error(
                                "Unexpected error downloading file %s: %s", file_path, str(error)
                            )
                            self._report_error(f"Unexpected download error: {str(error)}")

                    # Schedule next batch
                    if not self._cancelled and not self._getter.stop_doing:
                        for next_file in itertools.islice(file_iterator, new_tasks):
                            self._schedule_download(next_file)

            success = (
                not self._cancelled
                and not self._getter.stop_doing
                and self._completed_files == self._total_files
            )
            if success:
                self._update_progress("completed", "All downloads completed successfully")
            else:
                self._update_progress("error", "Download incomplete or cancelled")

            return success

        except (
            dds_cli.exceptions.DownloadError,
            dds_cli.exceptions.ApiRequestError,
            OSError,
            RuntimeError,
        ) as error:
            LOG.error("Download operation failed: %s", str(error))
            self._report_error(f"Download failed: {str(error)}")
            return False
        except Exception as error:  # pylint: disable=broad-exception-caught
            LOG.error("Unexpected error during download operation: %s", str(error))
            self._report_error(f"Unexpected download error: {str(error)}")
            return False
        finally:
            self._is_downloading = False
            self._executor = None
            self._download_threads.clear()

    def download_file(self, file_path: str) -> DownloadResult:
        """Download a single file.

        Args:
            file_path: Path to file to download

        Returns:
            DownloadResult with success status and details
        """
        if not self._is_initialized:
            return DownloadResult(
                success=False, file_path=file_path, error_message="Downloader not initialized"
            )

        if file_path not in self._getter.filehandler.data:
            return DownloadResult(
                success=False, file_path=file_path, error_message="File not found in project"
            )

        try:
            # Get file size for progress tracking
            file_size = self._getter.filehandler.data[file_path]["size_stored"]

            # Create callback-aware progress object for single file download
            progress = CallbackProgress(
                progress_callback=self._progress_callback,
                file_path=file_path,
                total_size=file_size,
                downloader_instance=self,
            )

            success, message = self._getter.download_and_verify(file=file_path, progress=progress)

            return DownloadResult(
                success=success, file_path=file_path, error_message=message if not success else None
            )

        except (
            dds_cli.exceptions.DownloadError,
            dds_cli.exceptions.ApiRequestError,
            OSError,
            RuntimeError,
        ) as error:
            LOG.error("Single file download error for %s: %s", file_path, str(error))
            return DownloadResult(success=False, file_path=file_path, error_message=str(error))
        except Exception as error:  # pylint: disable=broad-exception-caught
            LOG.error("Unexpected error downloading single file %s: %s", file_path, str(error))
            return DownloadResult(
                success=False, file_path=file_path, error_message=f"Unexpected error: {str(error)}"
            )

    def cancel_download(self) -> None:
        """Cancel ongoing download operations."""
        try:
            self._cancelled = True
            self._is_downloading = False

            # Set stop_doing flag on the underlying DataGetter to stop ongoing downloads
            if self._getter:
                self._getter.stop_doing = True

            if self._executor:
                # Cancel pending futures
                for future in self._download_threads:
                    future.cancel()
                self._download_threads.clear()

            # Update progress with error handling
            try:
                self._update_progress("error", "Download cancelled by user")
            except (OSError, RuntimeError) as error:
                LOG.warning("Error updating progress during cancellation: %s", error)
            except Exception as error:  # pylint: disable=broad-exception-caught
                LOG.warning("Unexpected error updating progress during cancellation: %s", error)

        except (OSError, RuntimeError) as error:
            LOG.error("Error during download cancellation: %s", error)
            # Still set the flags even if there's an error
            try:
                self._cancelled = True
                self._is_downloading = False
                if self._getter:
                    self._getter.stop_doing = True
            except Exception as final_error:  # pylint: disable=broad-exception-caught
                LOG.error("Error setting cancellation flags: %s", final_error)
        except Exception as error:  # pylint: disable=broad-exception-caught
            LOG.error("Unexpected error during download cancellation: %s", error)
            # Still set the flags even if there's an error
            try:
                self._cancelled = True
                self._is_downloading = False
                if self._getter:
                    self._getter.stop_doing = True
            except Exception as final_error:  # pylint: disable=broad-exception-caught
                LOG.error("Error setting cancellation flags: %s", final_error)

    def get_file_list(self) -> List[str]:
        """Get list of files available for download.

        Returns:
            List of file paths
        """
        if not self._is_initialized or not self._getter:
            return []

        return list(self._getter.filehandler.data.keys())

    def get_file_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific file.

        Args:
            file_path: Path to file

        Returns:
            File information dictionary or None if not found
        """
        if not self._is_initialized or not self._getter:
            return None

        return self._getter.filehandler.data.get(file_path)

    def cleanup(self) -> None:
        """Clean up resources and temporary files."""
        if self._is_downloading:
            self.cancel_download()

        if self._getter and hasattr(self._getter, "temporary_directory"):
            if self._getter.temporary_directory and self._getter.temporary_directory.is_dir():
                dds_cli.utils.delete_folder(self._getter.temporary_directory)

    def _schedule_download(self, file_path: str) -> None:
        """Schedule a file download in the thread pool."""
        if self._executor and not self._cancelled and not self._getter.stop_doing:
            # Get file size for progress tracking
            file_size = self._getter.filehandler.data[file_path]["size_stored"]

            # Create callback-aware progress object
            progress = CallbackProgress(
                progress_callback=self._progress_callback,
                file_path=file_path,
                total_size=file_size,
                downloader_instance=self,
            )

            future = self._executor.submit(
                self._getter.download_and_verify, file=file_path, progress=progress
            )
            self._download_threads[future] = file_path

    def _update_download_progress(self, current_file: str) -> None:
        """Update progress during download operations."""
        with self._progress_lock:
            overall_progress = self._completed_files / max(self._total_files, 1)
            overall_percentage = overall_progress * 100.0

            progress_info = DownloadProgress(
                current_file=current_file,
                total_files=self._total_files,
                completed_files=self._completed_files,
                error_files=self._error_files,
                current_file_progress=0.0,  # Individual file progress not tracked
                overall_progress=overall_progress,
                overall_percentage=overall_percentage,
                status="downloading",
                error_message=None,
                bytes_downloaded=0,
                total_bytes=0,
            )

            if self._progress_callback:
                self.safe_callback_execution(lambda: self._progress_callback(progress_info))

    def _update_progress(
        self, status: str, _message: str, error_message: Optional[str] = None
    ) -> None:
        """Update progress and notify callbacks.

        Args:
            status: Current status
            message: Status message (unused, kept for compatibility)
            error_message: Optional error message
        """
        try:
            with self._progress_lock:
                overall_progress = self._completed_files / max(self._total_files, 1)
                overall_percentage = overall_progress * 100.0

                progress_info = DownloadProgress(
                    current_file="",
                    total_files=self._total_files,
                    completed_files=self._completed_files,
                    error_files=self._error_files,
                    current_file_progress=0.0,
                    overall_progress=overall_progress,
                    overall_percentage=overall_percentage,
                    status=status,
                    error_message=error_message,
                    bytes_downloaded=0,
                    total_bytes=0,
                )

                if self._progress_callback:
                    self.safe_callback_execution(lambda: self._progress_callback(progress_info))

        except (OSError, RuntimeError) as error:
            LOG.warning("Error updating progress: %s", error)
        except Exception as error:  # pylint: disable=broad-exception-caught
            LOG.warning("Unexpected error updating progress: %s", error)

    def _report_error(self, message: str) -> None:
        """Report an error and notify callbacks."""
        self._update_progress("error", message, error_message=message)

        if self._error_callback:
            self.safe_callback_execution(lambda: self._error_callback(message))

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.cleanup()
