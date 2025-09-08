"""Integration tests for ProjectDownloader with DDS system."""

import pathlib
from unittest.mock import MagicMock, patch
from typing import List

import pytest

import dds_cli.exceptions
from dds_cli.dds_gui.utils.project_downloader import (
    ProjectDownloader,
    DownloadProgress,
    DownloadResult,
)


class TestProjectDownloaderIntegration:
    """Integration tests for ProjectDownloader with DDS system."""

    @pytest.fixture
    def mock_dds_system(self):
        """Create a comprehensive mock of the DDS system."""
        # Mock staging directory
        mock_staging_dir = MagicMock()
        mock_staging_dir.directories = {
            "FILES": pathlib.Path("/tmp/dds/files"),
            "LOGS": pathlib.Path("/tmp/dds/logs"),
        }

        # Mock file handler with realistic data
        mock_file_handler = MagicMock()
        mock_file_handler.data = {
            "data/experiment1/measurements.csv": {
                "name_in_db": "measurements.csv",
                "size_original": 1024000,
                "size_stored": 512000,
                "compressed": True,
                "checksum": "abc123def456",
                "public_key": "pubkey123",
                "salt": "salt123",
                "url": "https://api.example.com/files/measurements.csv",
                "path_downloaded": pathlib.Path("/tmp/dds/files/measurements.csv.tmp"),
            },
            "data/experiment1/results.json": {
                "name_in_db": "results.json",
                "size_original": 2048000,
                "size_stored": 1024000,
                "compressed": False,
                "checksum": "def456ghi789",
                "public_key": "pubkey456",
                "salt": "salt456",
                "url": "https://api.example.com/files/results.json",
                "path_downloaded": pathlib.Path("/tmp/dds/files/results.json.tmp"),
            },
            "data/experiment2/analysis.py": {
                "name_in_db": "analysis.py",
                "size_original": 512000,
                "size_stored": 256000,
                "compressed": True,
                "checksum": "ghi789jkl012",
                "public_key": "pubkey789",
                "salt": "salt789",
                "url": "https://api.example.com/files/analysis.py",
                "path_downloaded": pathlib.Path("/tmp/dds/files/analysis.py.tmp"),
            },
        }
        mock_file_handler.failed = []
        mock_file_handler.create_download_status_dict.return_value = {
            "total_files": 3,
            "total_size": 3584000,
        }

        # Mock data getter
        mock_data_getter = MagicMock()
        mock_data_getter.filehandler = mock_file_handler
        mock_data_getter.temporary_directory = pathlib.Path("/tmp/dds/temp")
        mock_data_getter.download_and_verify.return_value = (True, "")

        return {
            "staging_dir": mock_staging_dir,
            "file_handler": mock_file_handler,
            "data_getter": mock_data_getter,
        }

    @patch("dds_cli.dds_gui.utils.project_downloader.dds_cli.directory.DDSDirectory")
    @patch("dds_cli.dds_gui.utils.project_downloader.dds_cli.data_getter.DataGetter")
    def test_full_download_workflow(
        self, mock_data_getter_class, mock_directory_class, mock_dds_system
    ):
        """Test complete download workflow from initialization to completion."""
        # Setup mocks
        mock_data_getter_class.return_value = mock_dds_system["data_getter"]
        mock_directory_class.return_value = mock_dds_system["staging_dir"]

        # Track all callback calls
        progress_calls: List[DownloadProgress] = []
        file_completed_calls: List[DownloadResult] = []
        error_calls: List[str] = []

        def progress_callback(progress: DownloadProgress):
            progress_calls.append(progress)

        def file_completed_callback(result: DownloadResult):
            file_completed_calls.append(result)

        def error_callback(message: str):
            error_calls.append(message)

        # Create downloader and set up callbacks
        downloader = ProjectDownloader(
            project="test-project-123",
            destination=pathlib.Path("/tmp/downloads"),
            token_path="/tmp/token",
            no_prompt=True,
        )

        downloader.set_progress_callback(progress_callback)
        downloader.set_file_completed_callback(file_completed_callback)
        downloader.set_error_callback(error_callback)

        # Test initialization
        assert downloader.initialize(get_all=True) is True
        assert downloader._is_initialized is True
        assert downloader._total_files == 3

        # Verify file list
        files = downloader.get_file_list()
        assert len(files) == 3
        assert "data/experiment1/measurements.csv" in files
        assert "data/experiment1/results.json" in files
        assert "data/experiment2/analysis.py" in files

        # Test file info retrieval
        file_info = downloader.get_file_info("data/experiment1/measurements.csv")
        assert file_info is not None
        assert file_info["name_in_db"] == "measurements.csv"
        assert file_info["size_original"] == 1024000
        assert file_info["compressed"] is True

        # Test download all
        result = downloader.download_all(num_threads=2)
        assert result is True

        # Verify callbacks were called
        assert len(progress_calls) > 0
        assert len(file_completed_calls) == 3
        assert len(error_calls) == 0

        # Verify progress progression
        progress_percentages = [p.overall_percentage for p in progress_calls]
        assert all(0.0 <= p <= 100.0 for p in progress_percentages)
        assert progress_percentages[-1] == 100.0  # Should end at 100%

        # Verify file completion results
        for result in file_completed_calls:
            assert result.success is True
            assert result.error_message is None
            assert result.file_path in files

    @patch("dds_cli.dds_gui.utils.project_downloader.dds_cli.directory.DDSDirectory")
    @patch("dds_cli.dds_gui.utils.project_downloader.dds_cli.data_getter.DataGetter")
    def test_selective_download(
        self, mock_data_getter_class, mock_directory_class, mock_dds_system
    ):
        """Test downloading specific files only."""
        # Setup mocks
        mock_data_getter_class.return_value = mock_dds_system["data_getter"]
        mock_directory_class.return_value = mock_dds_system["staging_dir"]

        # Filter file handler data to only include specific files
        mock_dds_system["file_handler"].data = {
            k: v
            for k, v in mock_dds_system["file_handler"].data.items()
            if k in ["data/experiment1/measurements.csv", "data/experiment1/results.json"]
        }

        downloader = ProjectDownloader(project="test-project-123")

        # Initialize with specific files
        assert (
            downloader.initialize(
                get_all=False,
                source=("data/experiment1/measurements.csv", "data/experiment1/results.json"),
            )
            is True
        )

        assert downloader._total_files == 2

        # Download all specified files
        result = downloader.download_all()
        assert result is True

    @patch("dds_cli.dds_gui.utils.project_downloader.dds_cli.directory.DDSDirectory")
    @patch("dds_cli.dds_gui.utils.project_downloader.dds_cli.data_getter.DataGetter")
    def test_single_file_download(
        self, mock_data_getter_class, mock_directory_class, mock_dds_system
    ):
        """Test downloading a single file."""
        # Setup mocks
        mock_data_getter_class.return_value = mock_dds_system["data_getter"]
        mock_directory_class.return_value = mock_dds_system["staging_dir"]

        downloader = ProjectDownloader(project="test-project-123")
        downloader.initialize(get_all=True)

        # Download single file
        result = downloader.download_file("data/experiment1/measurements.csv")

        assert result.success is True
        assert result.file_path == "data/experiment1/measurements.csv"
        assert result.error_message is None

    @patch("dds_cli.dds_gui.utils.project_downloader.dds_cli.directory.DDSDirectory")
    @patch("dds_cli.dds_gui.utils.project_downloader.dds_cli.data_getter.DataGetter")
    def test_download_with_failures(
        self, mock_data_getter_class, mock_directory_class, mock_dds_system
    ):
        """Test download with some files failing."""

        # Setup mocks with some failures
        def mock_download_and_verify(file, progress):
            if "results.json" in file:
                return False, "Network timeout"
            return True, ""

        mock_dds_system["data_getter"].download_and_verify.side_effect = mock_download_and_verify
        mock_data_getter_class.return_value = mock_dds_system["data_getter"]
        mock_directory_class.return_value = mock_dds_system["staging_dir"]

        file_completed_calls: List[DownloadResult] = []

        def file_completed_callback(result: DownloadResult):
            file_completed_calls.append(result)

        downloader = ProjectDownloader(project="test-project-123")
        downloader.set_file_completed_callback(file_completed_callback)
        downloader.initialize(get_all=True)

        # Download all files
        result = downloader.download_all()
        assert result is True  # Overall should still succeed

        # Check results
        successes = [r for r in file_completed_calls if r.success]
        failures = [r for r in file_completed_calls if not r.success]

        assert len(successes) == 2
        assert len(failures) == 1
        assert failures[0].file_path == "data/experiment1/results.json"
        assert failures[0].error_message == "Network timeout"

    @patch("dds_cli.dds_gui.utils.project_downloader.dds_cli.directory.DDSDirectory")
    @patch("dds_cli.dds_gui.utils.project_downloader.dds_cli.data_getter.DataGetter")
    def test_cancellation(self, mock_data_getter_class, mock_directory_class, mock_dds_system):
        """Test download cancellation."""

        # Setup mocks with slow download to allow cancellation
        def slow_download_and_verify(file, progress):
            import time

            time.sleep(0.2)  # Make download slow enough to cancel
            return True, ""

        mock_dds_system["data_getter"].download_and_verify.side_effect = slow_download_and_verify
        mock_data_getter_class.return_value = mock_dds_system["data_getter"]
        mock_directory_class.return_value = mock_dds_system["staging_dir"]

        downloader = ProjectDownloader(project="test-project-123")
        downloader.initialize(get_all=True)

        # Start download in a separate thread
        import threading
        import time

        download_result = None

        def download_worker():
            nonlocal download_result
            download_result = downloader.download_all()

        download_thread = threading.Thread(target=download_worker)
        download_thread.start()

        # Cancel after a short delay
        time.sleep(0.1)
        downloader.cancel_download()

        download_thread.join()

        # Should be cancelled
        assert download_result is False
        assert downloader._cancelled is True

    @patch("dds_cli.dds_gui.utils.project_downloader.dds_cli.directory.DDSDirectory")
    @patch("dds_cli.dds_gui.utils.project_downloader.dds_cli.data_getter.DataGetter")
    def test_authentication_error(
        self, mock_data_getter_class, mock_directory_class, mock_dds_system
    ):
        """Test handling of authentication errors."""
        # Setup mocks to raise authentication error
        mock_data_getter_class.side_effect = dds_cli.exceptions.AuthenticationError("Invalid token")
        mock_directory_class.return_value = mock_dds_system["staging_dir"]

        downloader = ProjectDownloader(project="test-project-123")

        # Should fail to initialize
        result = downloader.initialize(get_all=True)
        assert result is False

    @patch("dds_cli.dds_gui.utils.project_downloader.dds_cli.directory.DDSDirectory")
    @patch("dds_cli.dds_gui.utils.project_downloader.dds_cli.data_getter.DataGetter")
    def test_api_error(self, mock_data_getter_class, mock_directory_class, mock_dds_system):
        """Test handling of API errors."""
        # Setup mocks to raise API error
        mock_data_getter_class.side_effect = dds_cli.exceptions.ApiRequestError("API unavailable")
        mock_directory_class.return_value = mock_dds_system["staging_dir"]

        downloader = ProjectDownloader(project="test-project-123")

        # Should fail to initialize
        result = downloader.initialize(get_all=True)
        assert result is False

    @patch("dds_cli.dds_gui.utils.project_downloader.dds_cli.directory.DDSDirectory")
    @patch("dds_cli.dds_gui.utils.project_downloader.dds_cli.data_getter.DataGetter")
    def test_context_manager_cleanup(
        self, mock_data_getter_class, mock_directory_class, mock_dds_system
    ):
        """Test that context manager properly cleans up resources."""
        # Setup the mock data getter with temporary directory
        mock_temp_dir = MagicMock()
        mock_temp_dir.is_dir.return_value = True
        mock_dds_system["data_getter"].temporary_directory = mock_temp_dir

        mock_data_getter_class.return_value = mock_dds_system["data_getter"]
        mock_directory_class.return_value = mock_dds_system["staging_dir"]

        with patch("dds_cli.utils.delete_folder") as mock_delete:
            with ProjectDownloader(project="test-project-123") as downloader:
                downloader.initialize(get_all=True)
                # Simulate some downloads and set up the getter for cleanup
                downloader._is_downloading = True
                downloader._getter = mock_dds_system["data_getter"]

            # Should clean up on exit
            mock_delete.assert_called_once()

    def test_progress_calculation_accuracy(self):
        """Test that progress calculations are accurate."""
        downloader = ProjectDownloader(project="test-project")
        downloader._total_files = 10
        downloader._completed_files = 0

        progress_calls: List[DownloadProgress] = []

        def progress_callback(progress: DownloadProgress):
            progress_calls.append(progress)

        downloader.set_progress_callback(progress_callback)

        # Test various completion levels
        test_cases = [
            (0, 0.0, 0.0),
            (1, 0.1, 10.0),
            (5, 0.5, 50.0),
            (9, 0.9, 90.0),
            (10, 1.0, 100.0),
        ]

        for completed, expected_progress, expected_percentage in test_cases:
            downloader._completed_files = completed
            downloader._update_download_progress("test.txt")

            progress = progress_calls[-1]
            assert progress.overall_progress == expected_progress
            assert progress.overall_percentage == expected_percentage
            assert progress.completed_files == completed
            assert progress.total_files == 10
