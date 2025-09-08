"""Tests for ProjectDownloader GUI utility class."""

import pathlib
import threading
import time
from unittest.mock import MagicMock, Mock, patch
from typing import List

import pytest

import dds_cli.exceptions
from dds_cli.dds_gui.utils.project_downloader import (
    ProjectDownloader,
    DownloadProgress,
    DownloadResult,
)


class TestDownloadProgress:
    """Test DownloadProgress dataclass."""

    def test_download_progress_creation(self):
        """Test creating DownloadProgress objects."""
        progress = DownloadProgress(
            current_file="test.txt",
            total_files=10,
            completed_files=5,
            current_file_progress=0.5,
            overall_progress=0.5,
            overall_percentage=50.0,
            status="downloading",
            error_message=None,
        )

        assert progress.current_file == "test.txt"
        assert progress.total_files == 10
        assert progress.completed_files == 5
        assert progress.current_file_progress == 0.5
        assert progress.overall_progress == 0.5
        assert progress.overall_percentage == 50.0
        assert progress.status == "downloading"
        assert progress.error_message is None

    def test_download_progress_with_error(self):
        """Test DownloadProgress with error message."""
        progress = DownloadProgress(
            current_file="",
            total_files=5,
            completed_files=0,
            current_file_progress=0.0,
            overall_progress=0.0,
            overall_percentage=0.0,
            status="error",
            error_message="Test error",
        )

        assert progress.status == "error"
        assert progress.error_message == "Test error"


class TestDownloadResult:
    """Test DownloadResult dataclass."""

    def test_download_result_success(self):
        """Test successful DownloadResult."""
        result = DownloadResult(
            success=True,
            file_path="/path/to/file.txt",
            error_message=None,
            file_size=1024,
        )

        assert result.success is True
        assert result.file_path == "/path/to/file.txt"
        assert result.error_message is None
        assert result.file_size == 1024

    def test_download_result_failure(self):
        """Test failed DownloadResult."""
        result = DownloadResult(
            success=False,
            file_path="/path/to/file.txt",
            error_message="Download failed",
        )

        assert result.success is False
        assert result.file_path == "/path/to/file.txt"
        assert result.error_message == "Download failed"
        assert result.file_size is None


class TestProjectDownloader:
    """Test ProjectDownloader class."""

    @pytest.fixture
    def mock_data_getter(self):
        """Create a mock DataGetter."""
        mock_getter = MagicMock()
        mock_getter.filehandler = MagicMock()
        mock_getter.filehandler.data = {
            "file1.txt": {"name_in_db": "file1.txt", "size_original": 1000},
            "file2.txt": {"name_in_db": "file2.txt", "size_original": 2000},
            "file3.txt": {"name_in_db": "file3.txt", "size_original": 3000},
        }
        mock_getter.download_and_verify.return_value = (True, "")
        return mock_getter

    @pytest.fixture
    def mock_staging_dir(self):
        """Create a mock staging directory."""
        mock_dir = MagicMock()
        mock_dir.directories = {"FILES": pathlib.Path("/tmp/files")}
        return mock_dir

    def test_init(self):
        """Test ProjectDownloader initialization."""
        downloader = ProjectDownloader(
            project="test-project",
            destination=pathlib.Path("/tmp/downloads"),
            token_path="/tmp/token",
            no_prompt=True,
        )

        assert downloader.project == "test-project"
        assert downloader.destination == pathlib.Path("/tmp/downloads")
        assert downloader.token_path == "/tmp/token"
        assert downloader.no_prompt is True
        assert downloader._is_initialized is False
        assert downloader._is_downloading is False
        assert downloader._cancelled is False

    def test_set_callbacks(self):
        """Test setting callback functions."""
        downloader = ProjectDownloader(project="test-project")

        def progress_callback(progress):
            pass

        def file_completed_callback(result):
            pass

        def error_callback(message):
            pass

        downloader.set_progress_callback(progress_callback)
        downloader.set_file_completed_callback(file_completed_callback)
        downloader.set_error_callback(error_callback)

        assert downloader._progress_callback == progress_callback
        assert downloader._file_completed_callback == file_completed_callback
        assert downloader._error_callback == error_callback

    @patch("dds_cli.dds_gui.utils.project_downloader.dds_cli.directory.DDSDirectory")
    @patch("dds_cli.dds_gui.utils.project_downloader.dds_cli.data_getter.DataGetter")
    def test_initialize_success(
        self, mock_data_getter_class, mock_directory_class, mock_data_getter, mock_staging_dir
    ):
        """Test successful initialization."""
        mock_data_getter_class.return_value = mock_data_getter
        mock_directory_class.return_value = mock_staging_dir

        downloader = ProjectDownloader(project="test-project")

        result = downloader.initialize(get_all=True)

        assert result is True
        assert downloader._is_initialized is True
        assert downloader._total_files == 3
        assert downloader._completed_files == 0

    @patch("dds_cli.dds_gui.utils.project_downloader.dds_cli.directory.DDSDirectory")
    @patch("dds_cli.dds_gui.utils.project_downloader.dds_cli.data_getter.DataGetter")
    def test_initialize_with_specific_files(
        self, mock_data_getter_class, mock_directory_class, mock_data_getter, mock_staging_dir
    ):
        """Test initialization with specific files."""
        mock_data_getter_class.return_value = mock_data_getter
        mock_directory_class.return_value = mock_staging_dir

        downloader = ProjectDownloader(project="test-project")

        result = downloader.initialize(
            get_all=False,
            source=("file1.txt", "file2.txt"),
            source_path_file=None,
        )

        assert result is True
        assert downloader._is_initialized is True

    @patch("dds_cli.dds_gui.utils.project_downloader.dds_cli.directory.DDSDirectory")
    @patch("dds_cli.dds_gui.utils.project_downloader.dds_cli.data_getter.DataGetter")
    def test_initialize_validation_errors(
        self, mock_data_getter_class, mock_directory_class, mock_data_getter, mock_staging_dir
    ):
        """Test initialization validation errors."""
        mock_data_getter_class.return_value = mock_data_getter
        mock_directory_class.return_value = mock_staging_dir

        downloader = ProjectDownloader(project="test-project")

        # Test get_all with source conflict
        result = downloader.initialize(
            get_all=True,
            source=("file1.txt",),
        )
        assert result is False

        # Test no source specified
        result = downloader.initialize(
            get_all=False,
            source=(),
        )
        assert result is False

    @patch("dds_cli.dds_gui.utils.project_downloader.dds_cli.directory.DDSDirectory")
    @patch("dds_cli.dds_gui.utils.project_downloader.dds_cli.data_getter.DataGetter")
    def test_initialize_no_files(
        self, mock_data_getter_class, mock_directory_class, mock_staging_dir
    ):
        """Test initialization with no files to download."""
        mock_getter = MagicMock()
        mock_getter.filehandler = MagicMock()
        mock_getter.filehandler.data = {}  # No files
        mock_data_getter_class.return_value = mock_getter
        mock_directory_class.return_value = mock_staging_dir

        downloader = ProjectDownloader(project="test-project")

        result = downloader.initialize(get_all=True)

        assert result is False

    @patch("dds_cli.dds_gui.utils.project_downloader.dds_cli.directory.DDSDirectory")
    @patch("dds_cli.dds_gui.utils.project_downloader.dds_cli.data_getter.DataGetter")
    def test_initialize_exception_handling(
        self, mock_data_getter_class, mock_directory_class, mock_staging_dir
    ):
        """Test initialization exception handling."""
        mock_data_getter_class.side_effect = dds_cli.exceptions.AuthenticationError("Auth failed")
        mock_directory_class.return_value = mock_staging_dir

        downloader = ProjectDownloader(project="test-project")

        result = downloader.initialize(get_all=True)

        assert result is False

    def test_download_all_not_initialized(self):
        """Test download_all when not initialized."""
        downloader = ProjectDownloader(project="test-project")

        result = downloader.download_all()

        assert result is False

    def test_download_all_already_downloading(self):
        """Test download_all when already downloading."""
        downloader = ProjectDownloader(project="test-project")
        downloader._is_initialized = True
        downloader._is_downloading = True

        result = downloader.download_all()

        assert result is False

    @patch("dds_cli.dds_gui.utils.project_downloader.dds_cli.directory.DDSDirectory")
    @patch("dds_cli.dds_gui.utils.project_downloader.dds_cli.data_getter.DataGetter")
    def test_download_all_success(
        self, mock_data_getter_class, mock_directory_class, mock_data_getter, mock_staging_dir
    ):
        """Test successful download_all."""
        mock_data_getter_class.return_value = mock_data_getter
        mock_directory_class.return_value = mock_staging_dir

        downloader = ProjectDownloader(project="test-project")
        downloader.initialize(get_all=True)

        # Mock the progress callback to track calls
        progress_calls = []

        def progress_callback(progress):
            progress_calls.append(progress)

        downloader.set_progress_callback(progress_callback)

        result = downloader.download_all(num_threads=2)

        assert result is True
        assert len(progress_calls) > 0  # Should have progress updates

    @patch("dds_cli.dds_gui.utils.project_downloader.dds_cli.directory.DDSDirectory")
    @patch("dds_cli.dds_gui.utils.project_downloader.dds_cli.data_getter.DataGetter")
    def test_download_all_with_callbacks(
        self, mock_data_getter_class, mock_directory_class, mock_data_getter, mock_staging_dir
    ):
        """Test download_all with callbacks."""
        mock_data_getter_class.return_value = mock_data_getter
        mock_directory_class.return_value = mock_staging_dir

        downloader = ProjectDownloader(project="test-project")
        downloader.initialize(get_all=True)

        # Track callback calls
        progress_calls = []
        file_completed_calls = []
        error_calls = []

        def progress_callback(progress):
            progress_calls.append(progress)

        def file_completed_callback(result):
            file_completed_calls.append(result)

        def error_callback(message):
            error_calls.append(message)

        downloader.set_progress_callback(progress_callback)
        downloader.set_file_completed_callback(file_completed_callback)
        downloader.set_error_callback(error_callback)

        result = downloader.download_all(num_threads=1)

        assert result is True
        assert len(progress_calls) > 0
        assert len(file_completed_calls) == 3  # One for each file
        assert len(error_calls) == 0

    def test_download_file_not_initialized(self):
        """Test download_file when not initialized."""
        downloader = ProjectDownloader(project="test-project")

        result = downloader.download_file("file1.txt")

        assert result.success is False
        assert result.error_message == "Downloader not initialized"

    @patch("dds_cli.dds_gui.utils.project_downloader.dds_cli.directory.DDSDirectory")
    @patch("dds_cli.dds_gui.utils.project_downloader.dds_cli.data_getter.DataGetter")
    def test_download_file_file_not_found(
        self, mock_data_getter_class, mock_directory_class, mock_data_getter, mock_staging_dir
    ):
        """Test download_file with file not found."""
        mock_data_getter_class.return_value = mock_data_getter
        mock_directory_class.return_value = mock_staging_dir

        downloader = ProjectDownloader(project="test-project")
        downloader.initialize(get_all=True)

        result = downloader.download_file("nonexistent.txt")

        assert result.success is False
        assert result.error_message == "File not found in project"

    @patch("dds_cli.dds_gui.utils.project_downloader.dds_cli.directory.DDSDirectory")
    @patch("dds_cli.dds_gui.utils.project_downloader.dds_cli.data_getter.DataGetter")
    def test_download_file_success(
        self, mock_data_getter_class, mock_directory_class, mock_data_getter, mock_staging_dir
    ):
        """Test successful download_file."""
        mock_data_getter_class.return_value = mock_data_getter
        mock_directory_class.return_value = mock_staging_dir

        downloader = ProjectDownloader(project="test-project")
        downloader.initialize(get_all=True)

        result = downloader.download_file("file1.txt")

        assert result.success is True
        assert result.file_path == "file1.txt"
        assert result.error_message is None

    @patch("dds_cli.dds_gui.utils.project_downloader.dds_cli.directory.DDSDirectory")
    @patch("dds_cli.dds_gui.utils.project_downloader.dds_cli.data_getter.DataGetter")
    def test_download_file_failure(
        self, mock_data_getter_class, mock_directory_class, mock_data_getter, mock_staging_dir
    ):
        """Test failed download_file."""
        mock_data_getter_class.return_value = mock_data_getter
        mock_directory_class.return_value = mock_staging_dir
        mock_data_getter.download_and_verify.return_value = (False, "Download failed")

        downloader = ProjectDownloader(project="test-project")
        downloader.initialize(get_all=True)

        result = downloader.download_file("file1.txt")

        assert result.success is False
        assert result.file_path == "file1.txt"
        assert result.error_message == "Download failed"

    def test_cancel_download(self):
        """Test cancel_download."""
        downloader = ProjectDownloader(project="test-project")
        downloader._cancelled = False
        downloader._executor = MagicMock()
        downloader._download_threads = {MagicMock(): "file1.txt"}

        downloader.cancel_download()

        assert downloader._cancelled is True

    def test_get_file_list_not_initialized(self):
        """Test get_file_list when not initialized."""
        downloader = ProjectDownloader(project="test-project")

        result = downloader.get_file_list()

        assert result == []

    @patch("dds_cli.dds_gui.utils.project_downloader.dds_cli.directory.DDSDirectory")
    @patch("dds_cli.dds_gui.utils.project_downloader.dds_cli.data_getter.DataGetter")
    def test_get_file_list_success(
        self, mock_data_getter_class, mock_directory_class, mock_data_getter, mock_staging_dir
    ):
        """Test successful get_file_list."""
        mock_data_getter_class.return_value = mock_data_getter
        mock_directory_class.return_value = mock_staging_dir

        downloader = ProjectDownloader(project="test-project")
        downloader.initialize(get_all=True)

        result = downloader.get_file_list()

        assert len(result) == 3
        assert "file1.txt" in result
        assert "file2.txt" in result
        assert "file3.txt" in result

    def test_get_file_info_not_initialized(self):
        """Test get_file_info when not initialized."""
        downloader = ProjectDownloader(project="test-project")

        result = downloader.get_file_info("file1.txt")

        assert result is None

    @patch("dds_cli.dds_gui.utils.project_downloader.dds_cli.directory.DDSDirectory")
    @patch("dds_cli.dds_gui.utils.project_downloader.dds_cli.data_getter.DataGetter")
    def test_get_file_info_success(
        self, mock_data_getter_class, mock_directory_class, mock_data_getter, mock_staging_dir
    ):
        """Test successful get_file_info."""
        mock_data_getter_class.return_value = mock_data_getter
        mock_directory_class.return_value = mock_staging_dir

        downloader = ProjectDownloader(project="test-project")
        downloader.initialize(get_all=True)

        result = downloader.get_file_info("file1.txt")

        assert result is not None
        assert result["name_in_db"] == "file1.txt"
        assert result["size_original"] == 1000

    @patch("dds_cli.dds_gui.utils.project_downloader.dds_cli.directory.DDSDirectory")
    @patch("dds_cli.dds_gui.utils.project_downloader.dds_cli.data_getter.DataGetter")
    def test_get_file_info_not_found(
        self, mock_data_getter_class, mock_directory_class, mock_data_getter, mock_staging_dir
    ):
        """Test get_file_info with file not found."""
        mock_data_getter_class.return_value = mock_data_getter
        mock_directory_class.return_value = mock_staging_dir

        downloader = ProjectDownloader(project="test-project")
        downloader.initialize(get_all=True)

        result = downloader.get_file_info("nonexistent.txt")

        assert result is None

    def test_cleanup(self):
        """Test cleanup method."""
        downloader = ProjectDownloader(project="test-project")
        downloader._is_downloading = True
        downloader._getter = MagicMock()

        # Create a proper mock for the temporary directory
        mock_temp_dir = MagicMock()
        mock_temp_dir.is_dir.return_value = True
        downloader._getter.temporary_directory = mock_temp_dir

        with patch("dds_cli.utils.delete_folder") as mock_delete:
            downloader.cleanup()

            assert downloader._is_downloading is False
            mock_delete.assert_called_once()

    def test_context_manager(self):
        """Test using ProjectDownloader as context manager."""
        with patch("dds_cli.dds_gui.utils.project_downloader.dds_cli.directory.DDSDirectory"):
            with patch("dds_cli.dds_gui.utils.project_downloader.dds_cli.data_getter.DataGetter"):
                with ProjectDownloader(project="test-project") as downloader:
                    assert downloader.project == "test-project"

    def test_progress_calculation(self):
        """Test progress calculation methods."""
        downloader = ProjectDownloader(project="test-project")
        downloader._total_files = 10
        downloader._completed_files = 3

        # Test _update_download_progress
        progress_calls = []

        def progress_callback(progress):
            progress_calls.append(progress)

        downloader.set_progress_callback(progress_callback)
        downloader._update_download_progress("test.txt")

        assert len(progress_calls) == 1
        progress = progress_calls[0]
        assert progress.overall_progress == 0.3
        assert progress.overall_percentage == 30.0
        assert progress.current_file == "test.txt"
        assert progress.status == "downloading"

    def test_error_reporting(self):
        """Test error reporting."""
        downloader = ProjectDownloader(project="test-project")

        error_calls = []

        def error_callback(message):
            error_calls.append(message)

        downloader.set_error_callback(error_callback)
        downloader._report_error("Test error")

        assert len(error_calls) == 1
        assert error_calls[0] == "Test error"

    @patch("dds_cli.dds_gui.utils.project_downloader.dds_cli.directory.DDSDirectory")
    @patch("dds_cli.dds_gui.utils.project_downloader.dds_cli.data_getter.DataGetter")
    def test_download_all_with_failures(
        self, mock_data_getter_class, mock_directory_class, mock_data_getter, mock_staging_dir
    ):
        """Test download_all with some failures."""

        # Mock some files to fail
        def mock_download_and_verify(file, progress):
            if file == "file2.txt":
                return False, "Download failed"
            return True, ""

        mock_data_getter.download_and_verify.side_effect = mock_download_and_verify
        mock_data_getter_class.return_value = mock_data_getter
        mock_directory_class.return_value = mock_staging_dir

        downloader = ProjectDownloader(project="test-project")
        downloader.initialize(get_all=True)

        file_completed_calls = []

        def file_completed_callback(result):
            file_completed_calls.append(result)

        downloader.set_file_completed_callback(file_completed_callback)

        result = downloader.download_all(num_threads=1)

        # Should still complete successfully overall
        assert result is True
        assert len(file_completed_calls) == 3

        # Check that we have both successes and failures
        successes = [r for r in file_completed_calls if r.success]
        failures = [r for r in file_completed_calls if not r.success]

        assert len(successes) == 2
        assert len(failures) == 1
        assert failures[0].file_path == "file2.txt"
        assert failures[0].error_message == "Download failed"

    def test_threading_safety(self):
        """Test that progress updates are thread-safe."""
        downloader = ProjectDownloader(project="test-project")
        downloader._total_files = 100
        downloader._completed_files = 0

        progress_calls = []

        def progress_callback(progress):
            progress_calls.append(progress.overall_percentage)

        downloader.set_progress_callback(progress_callback)

        # Simulate concurrent progress updates
        def update_progress():
            for _ in range(10):
                downloader._completed_files += 1
                downloader._update_download_progress("test.txt")
                time.sleep(0.001)

        threads = []
        for _ in range(5):
            thread = threading.Thread(target=update_progress)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Should have 50 progress updates (5 threads * 10 updates each)
        assert len(progress_calls) == 50
        # All progress values should be valid percentages
        for progress in progress_calls:
            assert 0.0 <= progress <= 100.0
