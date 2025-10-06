"""Tests for ProjectDownloader GUI utility class."""

import concurrent.futures
import pathlib
import threading
import time
from unittest.mock import MagicMock, Mock, patch
from typing import List

import pytest

import dds_cli.exceptions
from dds_cli.dds_gui.pages.project_actions.download_data.project_downloader import (
    ProjectDownloader,
    DownloadProgress,
    DownloadResult,
    CallbackProgress,
)


def test_download_progress_creation():
    """Test creating DownloadProgress objects."""
    progress = DownloadProgress(
        current_file="test.txt",
        total_files=10,
        completed_files=5,
        error_files=1,
        current_file_progress=0.5,
        overall_progress=0.5,
        overall_percentage=50.0,
        status="downloading",
        error_message=None,
    )

    assert progress.current_file == "test.txt"
    assert progress.total_files == 10
    assert progress.completed_files == 5
    assert progress.error_files == 1
    assert progress.current_file_progress == 0.5
    assert progress.overall_progress == 0.5
    assert progress.overall_percentage == 50.0
    assert progress.status == "downloading"
    assert progress.error_message is None


def test_download_progress_with_error():
    """Test DownloadProgress with error message."""
    progress = DownloadProgress(
        current_file="",
        total_files=5,
        completed_files=0,
        error_files=1,
        current_file_progress=0.0,
        overall_progress=0.0,
        overall_percentage=0.0,
        status="error",
        error_message="Test error",
    )

    assert progress.status == "error"
    assert progress.error_message == "Test error"


def test_download_result_success():
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


def test_download_result_failure():
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


@pytest.fixture
def mock_data_getter():
    """Create a mock DataGetter."""
    mock_getter = MagicMock()
    mock_getter.filehandler = MagicMock()
    mock_getter.filehandler.data = {
        "file1.txt": {"name_in_db": "file1.txt", "size_original": 1000, "size_stored": 1000},
        "file2.txt": {"name_in_db": "file2.txt", "size_original": 2000, "size_stored": 2000},
        "file3.txt": {"name_in_db": "file3.txt", "size_original": 3000, "size_stored": 3000},
    }
    mock_getter.download_and_verify.return_value = (True, "")
    return mock_getter


@pytest.fixture
def mock_staging_dir():
    """Create a mock staging directory."""
    mock_dir = MagicMock()
    mock_dir.directories = {"FILES": pathlib.Path("/tmp/files")}
    return mock_dir


def test_init():
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


def test_set_callbacks():
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


@patch(
    "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.directory.DDSDirectory"
)
@patch(
    "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.data_getter.DataGetter"
)
def test_initialize_success(
    mock_data_getter_class, mock_directory_class, mock_data_getter, mock_staging_dir
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


@patch(
    "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.directory.DDSDirectory"
)
@patch(
    "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.data_getter.DataGetter"
)
def test_initialize_with_specific_files(
    mock_data_getter_class, mock_directory_class, mock_data_getter, mock_staging_dir
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


@patch(
    "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.directory.DDSDirectory"
)
@patch(
    "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.data_getter.DataGetter"
)
def test_initialize_validation_errors(
    mock_data_getter_class, mock_directory_class, mock_data_getter, mock_staging_dir
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


@patch(
    "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.directory.DDSDirectory"
)
@patch(
    "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.data_getter.DataGetter"
)
def test_initialize_no_files(mock_data_getter_class, mock_directory_class, mock_staging_dir):
    """Test initialization with no files to download."""
    mock_getter = MagicMock()
    mock_getter.filehandler = MagicMock()
    mock_getter.filehandler.data = {}  # No files
    mock_data_getter_class.return_value = mock_getter
    mock_directory_class.return_value = mock_staging_dir

    downloader = ProjectDownloader(project="test-project")

    result = downloader.initialize(get_all=True)

    assert result is False


@patch(
    "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.directory.DDSDirectory"
)
@patch(
    "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.data_getter.DataGetter"
)
def test_initialize_exception_handling(
    mock_data_getter_class, mock_directory_class, mock_staging_dir
):
    """Test initialization exception handling."""
    mock_data_getter_class.side_effect = dds_cli.exceptions.AuthenticationError("Auth failed")
    mock_directory_class.return_value = mock_staging_dir

    downloader = ProjectDownloader(project="test-project")

    result = downloader.initialize(get_all=True)

    assert result is False


def test_download_all_not_initialized():
    """Test download_all when not initialized."""
    downloader = ProjectDownloader(project="test-project")

    result = downloader.download_all()

    assert result is False


def test_download_all_already_downloading():
    """Test download_all when already downloading."""
    downloader = ProjectDownloader(project="test-project")
    downloader._is_initialized = True
    downloader._is_downloading = True

    result = downloader.download_all()

    assert result is False


@patch(
    "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.directory.DDSDirectory"
)
@patch(
    "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.data_getter.DataGetter"
)
def test_download_all_success(
    mock_data_getter_class, mock_directory_class, mock_data_getter, mock_staging_dir
):
    """Test successful download_all."""
    mock_data_getter_class.return_value = mock_data_getter
    mock_directory_class.return_value = mock_staging_dir

    # Mock download_and_verify to return success
    mock_data_getter.download_and_verify.return_value = (True, "Download successful")
    mock_data_getter.stop_doing = False

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


@patch(
    "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.directory.DDSDirectory"
)
@patch(
    "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.data_getter.DataGetter"
)
def test_download_all_with_callbacks(
    mock_data_getter_class, mock_directory_class, mock_data_getter, mock_staging_dir
):
    """Test download_all with callbacks."""
    mock_data_getter_class.return_value = mock_data_getter
    mock_directory_class.return_value = mock_staging_dir

    # Mock download_and_verify to return success
    mock_data_getter.download_and_verify.return_value = (True, "Download successful")
    mock_data_getter.stop_doing = False

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


def test_download_file_not_initialized():
    """Test download_file when not initialized."""
    downloader = ProjectDownloader(project="test-project")

    result = downloader.download_file("file1.txt")

    assert result.success is False
    assert result.error_message == "Downloader not initialized"


@patch(
    "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.directory.DDSDirectory"
)
@patch(
    "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.data_getter.DataGetter"
)
def test_download_file_file_not_found(
    mock_data_getter_class, mock_directory_class, mock_data_getter, mock_staging_dir
):
    """Test download_file with file not found."""
    mock_data_getter_class.return_value = mock_data_getter
    mock_directory_class.return_value = mock_staging_dir

    downloader = ProjectDownloader(project="test-project")
    downloader.initialize(get_all=True)

    result = downloader.download_file("nonexistent.txt")

    assert result.success is False
    assert result.error_message == "File not found in project"


@patch(
    "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.directory.DDSDirectory"
)
@patch(
    "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.data_getter.DataGetter"
)
def test_download_file_success(
    mock_data_getter_class, mock_directory_class, mock_data_getter, mock_staging_dir
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


@patch(
    "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.directory.DDSDirectory"
)
@patch(
    "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.data_getter.DataGetter"
)
def test_download_file_failure(
    mock_data_getter_class, mock_directory_class, mock_data_getter, mock_staging_dir
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


def test_cancel_download():
    """Test cancel_download."""
    downloader = ProjectDownloader(project="test-project")
    downloader._cancelled = False
    downloader._executor = MagicMock()
    downloader._download_threads = {MagicMock(): "file1.txt"}

    downloader.cancel_download()

    assert downloader._cancelled is True


def test_get_file_list_not_initialized():
    """Test get_file_list when not initialized."""
    downloader = ProjectDownloader(project="test-project")

    result = downloader.get_file_list()

    assert result == []


@patch(
    "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.directory.DDSDirectory"
)
@patch(
    "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.data_getter.DataGetter"
)
def test_get_file_list_success(
    mock_data_getter_class, mock_directory_class, mock_data_getter, mock_staging_dir
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


def test_get_file_info_not_initialized():
    """Test get_file_info when not initialized."""
    downloader = ProjectDownloader(project="test-project")

    result = downloader.get_file_info("file1.txt")

    assert result is None


@patch(
    "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.directory.DDSDirectory"
)
@patch(
    "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.data_getter.DataGetter"
)
def test_get_file_info_success(
    mock_data_getter_class, mock_directory_class, mock_data_getter, mock_staging_dir
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


@patch(
    "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.directory.DDSDirectory"
)
@patch(
    "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.data_getter.DataGetter"
)
def test_get_file_info_not_found(
    mock_data_getter_class, mock_directory_class, mock_data_getter, mock_staging_dir
):
    """Test get_file_info with file not found."""
    mock_data_getter_class.return_value = mock_data_getter
    mock_directory_class.return_value = mock_staging_dir

    downloader = ProjectDownloader(project="test-project")
    downloader.initialize(get_all=True)

    result = downloader.get_file_info("nonexistent.txt")

    assert result is None


def test_cleanup():
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


def test_context_manager():
    """Test using ProjectDownloader as context manager."""
    with patch(
        "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.directory.DDSDirectory"
    ):
        with patch(
            "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.data_getter.DataGetter"
        ):
            with ProjectDownloader(project="test-project") as downloader:
                assert downloader.project == "test-project"


def test_progress_calculation():
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


def test_error_reporting():
    """Test error reporting."""
    downloader = ProjectDownloader(project="test-project")

    error_calls = []

    def error_callback(message):
        error_calls.append(message)

    downloader.set_error_callback(error_callback)
    downloader._report_error("Test error")

    assert len(error_calls) == 1
    assert error_calls[0] == "Test error"


@patch(
    "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.directory.DDSDirectory"
)
@patch(
    "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.data_getter.DataGetter"
)
def test_download_all_with_failures(
    mock_data_getter_class, mock_directory_class, mock_data_getter, mock_staging_dir
):
    """Test download_all with some failures."""

    # Mock some files to fail
    def mock_download_and_verify(file, progress):
        if file == "file2.txt":
            return False, "Download failed"
        return True, ""

    mock_data_getter.download_and_verify.side_effect = mock_download_and_verify
    mock_data_getter.stop_doing = False
    mock_data_getter_class.return_value = mock_data_getter
    mock_directory_class.return_value = mock_staging_dir

    downloader = ProjectDownloader(project="test-project")
    downloader.initialize(get_all=True)

    file_completed_calls = []

    def file_completed_callback(result):
        file_completed_calls.append(result)

    downloader.set_file_completed_callback(file_completed_callback)

    result = downloader.download_all(num_threads=1)

    # Should return False when some files fail
    assert result is False
    assert len(file_completed_calls) == 3

    # Check that we have both successes and failures
    successes = [r for r in file_completed_calls if r.success]
    failures = [r for r in file_completed_calls if not r.success]

    assert len(successes) == 2
    assert len(failures) == 1
    assert failures[0].file_path == "file2.txt"
    assert failures[0].error_message == "Download failed"


def test_threading_safety():
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


def test_callback_progress_init():
    """Test CallbackProgress initialization."""
    downloader = ProjectDownloader(project="test-project")
    progress = CallbackProgress(
        progress_callback=None,
        file_path="test.txt",
        total_size=1000,
        downloader_instance=downloader,
    )

    assert progress.downloader_instance == downloader
    assert progress.total_size == 1000
    assert progress.completed == 0
    assert progress.progress_callback is None


def test_callback_progress_trigger_no_callback():
    """Test CallbackProgress trigger with no callback."""
    downloader = ProjectDownloader(project="test-project")
    progress = CallbackProgress(
        progress_callback=None,
        file_path="test.txt",
        total_size=1000,
        downloader_instance=downloader,
    )

    # Should not raise exception
    progress._trigger_progress_callback()


def test_callback_progress_add_task():
    """Test CallbackProgress add_task method."""
    downloader = ProjectDownloader(project="test-project")
    progress = CallbackProgress(
        progress_callback=None,
        file_path="test.txt",
        total_size=1000,
        downloader_instance=downloader,
    )

    # Add a task
    task_id = progress.add_task("Downloading file", total=500)

    assert task_id == 0
    assert len(progress.tasks) == 1
    assert progress.tasks[0]["description"] == "Downloading file"
    assert progress.tasks[0]["total"] == 500
    assert progress.tasks[0]["completed"] == 0
    assert progress.tasks[0]["visible"] is True


def test_callback_progress_add_task_with_parameters():
    """Test CallbackProgress add_task method with all parameters."""
    downloader = ProjectDownloader(project="test-project")
    progress = CallbackProgress(
        progress_callback=None,
        file_path="test.txt",
        total_size=1000,
        downloader_instance=downloader,
    )

    # Add a task with all parameters
    task_id = progress.add_task("Processing", total=200, step=10, visible=False)

    assert task_id == 0
    assert progress.tasks[0]["description"] == "Processing"
    assert progress.tasks[0]["total"] == 200
    assert progress.tasks[0]["visible"] is False


def test_callback_progress_update_task():
    """Test CallbackProgress update method."""
    downloader = ProjectDownloader(project="test-project")
    progress = CallbackProgress(
        progress_callback=MagicMock(),
        file_path="test.txt",
        total_size=1000,
        downloader_instance=downloader,
    )

    # Add a task
    task_id = progress.add_task("Downloading")

    # Update task with advance
    progress.update(task_id, advance=100, description="Downloading chunk")

    assert progress.tasks[task_id]["completed"] == 100
    assert progress.tasks[task_id]["description"] == "Downloading chunk"
    assert progress.completed == 100


def test_callback_progress_update_task_description_only():
    """Test CallbackProgress update method with description only."""
    downloader = ProjectDownloader(project="test-project")
    progress = CallbackProgress(
        progress_callback=None,
        file_path="test.txt",
        total_size=1000,
        downloader_instance=downloader,
    )

    # Add a task
    task_id = progress.add_task("Downloading")

    # Update task description only
    progress.update(task_id, description="Processing")

    assert progress.tasks[task_id]["description"] == "Processing"
    assert progress.tasks[task_id]["completed"] == 0  # Should not change


def test_callback_progress_reset_task():
    """Test CallbackProgress reset method."""
    downloader = ProjectDownloader(project="test-project")
    progress = CallbackProgress(
        progress_callback=None,
        file_path="test.txt",
        total_size=1000,
        downloader_instance=downloader,
    )

    # Add a task and update it
    task_id = progress.add_task("Downloading", total=500)
    progress.update(task_id, advance=100)

    # Reset the task
    progress.reset(task_id, description="Restarted", total=300)

    assert progress.tasks[task_id]["completed"] == 0
    assert progress.tasks[task_id]["description"] == "Restarted"
    assert progress.tasks[task_id]["total"] == 300


def test_callback_progress_remove_task():
    """Test CallbackProgress remove_task method."""
    downloader = ProjectDownloader(project="test-project")
    progress = CallbackProgress(
        progress_callback=None,
        file_path="test.txt",
        total_size=1000,
        downloader_instance=downloader,
    )

    # Add a task
    task_id = progress.add_task("Downloading")

    # Remove the task
    progress.remove_task(task_id)

    assert task_id not in progress.tasks


def test_callback_progress_trigger_with_cancelled_downloader():
    """Test CallbackProgress trigger when downloader is cancelled."""
    downloader = ProjectDownloader(project="test-project")
    downloader._cancelled = True
    progress = CallbackProgress(
        progress_callback=MagicMock(),
        file_path="test.txt",
        total_size=1000,
        downloader_instance=downloader,
    )

    progress._trigger_progress_callback()

    # Should not call callback when cancelled
    progress.progress_callback.assert_not_called()


def test_callback_progress_trigger_with_stop_doing():
    """Test CallbackProgress trigger when stop_doing is True."""
    downloader = ProjectDownloader(project="test-project")
    downloader._getter = MagicMock()
    downloader._getter.stop_doing = True
    progress = CallbackProgress(
        progress_callback=MagicMock(),
        file_path="test.txt",
        total_size=1000,
        downloader_instance=downloader,
    )

    progress._trigger_progress_callback()

    # Should not call callback when stop_doing is True
    progress.progress_callback.assert_not_called()


def test_callback_progress_trigger_with_progress_callback_exception():
    """Test CallbackProgress trigger when callback raises exception."""
    downloader = ProjectDownloader(project="test-project")
    progress = CallbackProgress(
        progress_callback=MagicMock(side_effect=Exception("Callback failed")),
        file_path="test.txt",
        total_size=1000,
        downloader_instance=downloader,
    )

    # Should not raise exception
    progress._trigger_progress_callback()


def test_callback_progress_trigger_percentage_calculation():
    """Test CallbackProgress trigger percentage calculation."""
    downloader = ProjectDownloader(project="test-project")
    downloader._total_files = 10
    downloader._completed_files = 3
    downloader._total_bytes = 10000
    downloader._total_downloaded_bytes = 3000

    progress = CallbackProgress(
        progress_callback=MagicMock(),
        file_path="test.txt",
        total_size=1000,
        downloader_instance=downloader,
    )
    progress.completed = 500

    progress._trigger_progress_callback()

    # Verify callback was called
    progress.progress_callback.assert_called_once()
    call_args = progress.progress_callback.call_args[0][0]
    assert call_args.current_file == "test.txt"
    assert call_args.total_files == 10
    assert call_args.completed_files == 3


def test_callback_progress_trigger_fallback_calculation():
    """Test CallbackProgress trigger fallback calculation when total_bytes is 0."""
    downloader = ProjectDownloader(project="test-project")
    downloader._total_files = 5
    downloader._completed_files = 2
    downloader._total_bytes = 0  # No total bytes available
    downloader._total_downloaded_bytes = 0

    progress = CallbackProgress(
        progress_callback=MagicMock(),
        file_path="test.txt",
        total_size=1000,
        downloader_instance=downloader,
    )
    progress.completed = 500

    progress._trigger_progress_callback()

    # Verify callback was called with fallback calculation
    progress.progress_callback.assert_called_once()
    call_args = progress.progress_callback.call_args[0][0]
    assert call_args.total_files == 5
    assert call_args.completed_files == 2


def test_callback_progress_trigger_single_file_calculation():
    """Test CallbackProgress trigger calculation for single file."""
    downloader = ProjectDownloader(project="test-project")
    downloader._total_files = 1
    downloader._completed_files = 0
    downloader._total_bytes = 0
    downloader._total_downloaded_bytes = 0

    progress = CallbackProgress(
        progress_callback=MagicMock(),
        file_path="test.txt",
        total_size=1000,
        downloader_instance=downloader,
    )
    progress.completed = 500

    progress._trigger_progress_callback()

    # Verify callback was called
    progress.progress_callback.assert_called_once()
    call_args = progress.progress_callback.call_args[0][0]
    assert call_args.current_file_progress == 0.5  # 500/1000


def test_initialize_with_source_path_file():
    """Test initialization with source_path_file parameter."""
    with patch(
        "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.directory.DDSDirectory"
    ) as mock_directory_class, patch(
        "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.data_getter.DataGetter"
    ) as mock_data_getter_class:

        mock_data_getter = MagicMock()
        mock_data_getter.filehandler = MagicMock()
        mock_data_getter.filehandler.data = {
            "file1.txt": {"name_in_db": "file1.txt", "size_original": 1000, "size_stored": 1000},
        }
        mock_data_getter_class.return_value = mock_data_getter
        mock_directory_class.return_value = MagicMock()

        downloader = ProjectDownloader(project="test-project")

        # Create a temporary file for source_path_file
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("file1.txt\nfile2.txt\n")
            temp_file = f.name

        try:
            result = downloader.initialize(
                get_all=False,
                source=(),
                source_path_file=pathlib.Path(temp_file),
            )

            assert result is True
            assert downloader._is_initialized is True
        finally:
            import os

            os.unlink(temp_file)


def test_initialize_with_break_on_fail():
    """Test initialization with break_on_fail parameter."""
    with patch(
        "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.directory.DDSDirectory"
    ) as mock_directory_class, patch(
        "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.data_getter.DataGetter"
    ) as mock_data_getter_class:

        mock_data_getter = MagicMock()
        mock_data_getter.filehandler = MagicMock()
        mock_data_getter.filehandler.data = {
            "file1.txt": {"name_in_db": "file1.txt", "size_original": 1000, "size_stored": 1000},
        }
        mock_data_getter_class.return_value = mock_data_getter
        mock_directory_class.return_value = MagicMock()

        downloader = ProjectDownloader(project="test-project")

        result = downloader.initialize(
            get_all=True,
            break_on_fail=True,
            verify_checksum=True,
        )

        assert result is True
        assert downloader._is_initialized is True


def test_initialize_with_custom_destination():
    """Test initialization with custom destination."""
    with patch(
        "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.directory.DDSDirectory"
    ) as mock_directory_class, patch(
        "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.data_getter.DataGetter"
    ) as mock_data_getter_class:

        mock_data_getter = MagicMock()
        mock_data_getter.filehandler = MagicMock()
        mock_data_getter.filehandler.data = {
            "file1.txt": {"name_in_db": "file1.txt", "size_original": 1000, "size_stored": 1000},
        }
        mock_data_getter_class.return_value = mock_data_getter
        mock_directory_class.return_value = MagicMock()

        custom_dest = pathlib.Path("/custom/path")
        downloader = ProjectDownloader(project="test-project", destination=custom_dest)

        result = downloader.initialize(get_all=True)

        assert result is True
        assert downloader._is_initialized is True


def test_download_all_with_stop_doing_before_start():
    """Test download_all when stop_doing is True before starting."""
    with patch(
        "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.directory.DDSDirectory"
    ) as mock_directory_class, patch(
        "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.data_getter.DataGetter"
    ) as mock_data_getter_class:

        mock_data_getter = MagicMock()
        mock_data_getter.filehandler = MagicMock()
        mock_data_getter.filehandler.data = {
            "file1.txt": {"name_in_db": "file1.txt", "size_original": 1000, "size_stored": 1000},
        }
        mock_data_getter.stop_doing = True  # Set stop_doing before starting
        mock_data_getter_class.return_value = mock_data_getter
        mock_directory_class.return_value = MagicMock()

        downloader = ProjectDownloader(project="test-project")
        downloader.initialize(get_all=True)

        result = downloader.download_all()

        assert result is False
        assert downloader._is_downloading is False


def test_download_all_with_cancellation_during_execution():
    """Test download_all with cancellation during execution."""
    with patch(
        "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.directory.DDSDirectory"
    ) as mock_directory_class, patch(
        "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.data_getter.DataGetter"
    ) as mock_data_getter_class:

        mock_data_getter = MagicMock()
        mock_data_getter.filehandler = MagicMock()
        mock_data_getter.filehandler.data = {
            "file1.txt": {"name_in_db": "file1.txt", "size_original": 1000, "size_stored": 1000},
            "file2.txt": {"name_in_db": "file2.txt", "size_original": 2000, "size_stored": 2000},
        }
        mock_data_getter.download_and_verify.return_value = (True, "Success")
        mock_data_getter.stop_doing = False
        mock_data_getter_class.return_value = mock_data_getter
        mock_directory_class.return_value = MagicMock()

        downloader = ProjectDownloader(project="test-project")
        downloader.initialize(get_all=True)

        # Cancel during execution
        def mock_submit(func, *args, **kwargs):
            downloader._cancelled = True
            return MagicMock()

        with patch("concurrent.futures.ThreadPoolExecutor.submit", side_effect=mock_submit):
            result = downloader.download_all(num_threads=1)

        assert result is False


def test_download_all_with_future_cancelled():
    """Test download_all when future is cancelled."""
    with patch(
        "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.directory.DDSDirectory"
    ) as mock_directory_class, patch(
        "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.data_getter.DataGetter"
    ) as mock_data_getter_class:

        mock_data_getter = MagicMock()
        mock_data_getter.filehandler = MagicMock()
        mock_data_getter.filehandler.data = {
            "file1.txt": {"name_in_db": "file1.txt", "size_original": 1000, "size_stored": 1000},
        }
        mock_data_getter_class.return_value = mock_data_getter
        mock_directory_class.return_value = MagicMock()

        downloader = ProjectDownloader(project="test-project")
        downloader.initialize(get_all=True)

        # Create a cancelled future
        cancelled_future = MagicMock()
        cancelled_future.cancelled.return_value = True

        with patch("concurrent.futures.ThreadPoolExecutor") as mock_executor_class:
            mock_executor = MagicMock()
            mock_executor_class.return_value.__enter__.return_value = mock_executor
            mock_executor.submit.return_value = cancelled_future

            # Mock wait to return the cancelled future
            with patch("concurrent.futures.wait") as mock_wait:
                mock_wait.return_value = ([cancelled_future], [])

                result = downloader.download_all(num_threads=1)

                # Should handle cancelled future gracefully
                assert result is False


def test_download_all_with_future_exception():
    """Test download_all when future raises exception."""
    with patch(
        "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.directory.DDSDirectory"
    ) as mock_directory_class, patch(
        "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.data_getter.DataGetter"
    ) as mock_data_getter_class:

        mock_data_getter = MagicMock()
        mock_data_getter.filehandler = MagicMock()
        mock_data_getter.filehandler.data = {
            "file1.txt": {"name_in_db": "file1.txt", "size_original": 1000, "size_stored": 1000},
        }
        mock_data_getter_class.return_value = mock_data_getter
        mock_directory_class.return_value = MagicMock()

        downloader = ProjectDownloader(project="test-project")
        downloader.initialize(get_all=True)

        # Create a future that raises exception
        exception_future = MagicMock()
        exception_future.cancelled.return_value = False
        exception_future.result.side_effect = dds_cli.exceptions.DownloadError("Download failed")

        with patch("concurrent.futures.ThreadPoolExecutor") as mock_executor_class:
            mock_executor = MagicMock()
            mock_executor_class.return_value.__enter__.return_value = mock_executor
            mock_executor.submit.return_value = exception_future

            # Mock wait to return the exception future
            with patch("concurrent.futures.wait") as mock_wait:
                mock_wait.return_value = ([exception_future], [])

                with patch.object(downloader, "_report_error") as mock_report_error:
                    result = downloader.download_all(num_threads=1)

                    # Should handle exception gracefully and return False
                    assert result is False


def test_download_all_with_non_tuple_result():
    """Test download_all when download_and_verify returns non-tuple result."""
    with patch(
        "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.directory.DDSDirectory"
    ) as mock_directory_class, patch(
        "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.data_getter.DataGetter"
    ) as mock_data_getter_class:

        mock_data_getter = MagicMock()
        mock_data_getter.filehandler = MagicMock()
        mock_data_getter.filehandler.data = {
            "file1.txt": {"name_in_db": "file1.txt", "size_original": 1000, "size_stored": 1000},
        }
        mock_data_getter.download_and_verify.return_value = True  # Non-tuple result
        mock_data_getter.stop_doing = False
        mock_data_getter_class.return_value = mock_data_getter
        mock_directory_class.return_value = MagicMock()

        downloader = ProjectDownloader(project="test-project")
        downloader.initialize(get_all=True)

        result = downloader.download_all(num_threads=1)

        assert result is True

@pytest.mark.skip("Skipping timeout error test")
def test_download_all_with_timeout_error():
    """Test download_all with timeout error."""
    with patch(
        "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.directory.DDSDirectory"
    ) as mock_directory_class, patch(
        "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.data_getter.DataGetter"
    ) as mock_data_getter_class:

        mock_data_getter = MagicMock()
        mock_data_getter.filehandler = MagicMock()
        mock_data_getter.filehandler.data = {
            "file1.txt": {"name_in_db": "file1.txt", "size_original": 1000, "size_stored": 1000},
        }
        mock_data_getter.stop_doing = False
        mock_data_getter_class.return_value = mock_data_getter
        mock_directory_class.return_value = MagicMock()

        downloader = ProjectDownloader(project="test-project")
        downloader.initialize(get_all=True)

        with patch("concurrent.futures.ThreadPoolExecutor") as mock_executor_class:
            mock_executor = MagicMock()
            mock_executor_class.return_value.__enter__.return_value = mock_executor
            mock_executor.submit.return_value = MagicMock()

            # Mock wait to raise timeout error
            with patch("concurrent.futures.wait") as mock_wait:
                mock_wait.side_effect = concurrent.futures.TimeoutError()

                result = downloader.download_all(num_threads=1)

                # Should handle timeout gracefully
                assert result is False

@pytest.mark.skip("Skipping general exception test")
def test_download_all_with_general_exception():
    """Test download_all with general exception."""
    with patch(
        "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.directory.DDSDirectory"
    ) as mock_directory_class, patch(
        "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.data_getter.DataGetter"
    ) as mock_data_getter_class:

        mock_data_getter = MagicMock()
        mock_data_getter.filehandler = MagicMock()
        mock_data_getter.filehandler.data = {
            "file1.txt": {"name_in_db": "file1.txt", "size_original": 1000, "size_stored": 1000},
        }
        mock_data_getter_class.return_value = mock_data_getter
        mock_directory_class.return_value = MagicMock()

        downloader = ProjectDownloader(project="test-project")
        downloader.initialize(get_all=True)

        with patch("concurrent.futures.ThreadPoolExecutor") as mock_executor_class:
            mock_executor_class.side_effect = RuntimeError("Executor failed")

            with patch.object(downloader, "_report_error") as mock_report_error:
                result = downloader.download_all(num_threads=1)

                # Should handle exception gracefully
                mock_report_error.assert_called()
                assert result is False


def test_cancel_download_with_exception():
    """Test cancel_download with exception during cleanup."""
    downloader = ProjectDownloader(project="test-project")
    downloader._cancelled = False
    downloader._executor = MagicMock()
    downloader._download_threads = {MagicMock(): "file1.txt"}

    # Mock executor to raise exception
    downloader._executor = MagicMock()
    downloader._executor.shutdown.side_effect = Exception("Shutdown failed")

    # Should not raise exception
    downloader.cancel_download()

    assert downloader._cancelled is True


def test_cancel_download_fallback_error_handling():
    """Test cancel_download fallback error handling."""
    downloader = ProjectDownloader(project="test-project")
    downloader._cancelled = False
    downloader._executor = MagicMock()
    downloader._download_threads = {MagicMock(): "file1.txt"}

    # Mock getter to raise exception
    downloader._getter = MagicMock()
    downloader._getter.stop_doing = True

    # Mock progress update to raise exception
    with patch.object(downloader, "_update_progress") as mock_update:
        mock_update.side_effect = Exception("Progress update failed")

        # Should not raise exception
        downloader.cancel_download()

        assert downloader._cancelled is True


def test_safe_callback_execution_with_exception():
    """Test _safe_callback_execution with callback exception."""
    downloader = ProjectDownloader(project="test-project")

    def failing_callback():
        raise Exception("Callback failed")

    # Should not raise exception
    downloader._safe_callback_execution(failing_callback)


def test_safe_callback_execution_with_app_shutdown_error():
    """Test _safe_callback_execution with app shutdown error."""
    downloader = ProjectDownloader(project="test-project")

    def app_shutdown_callback():
        raise Exception("No active app")

    # Should not raise exception
    downloader._safe_callback_execution(app_shutdown_callback)


def test_safe_callback_execution_with_event_loop_error():
    """Test _safe_callback_execution with event loop error."""
    downloader = ProjectDownloader(project="test-project")

    def event_loop_callback():
        raise Exception("Event loop is closed")

    # Should not raise exception
    downloader._safe_callback_execution(event_loop_callback)


def test_update_progress_with_exception():
    """Test _update_progress with exception."""
    downloader = ProjectDownloader(project="test-project")
    downloader._total_files = 10
    downloader._completed_files = 3
    downloader._progress_callback = MagicMock(side_effect=Exception("Callback failed"))

    # Should not raise exception
    downloader._update_progress("downloading", "Test message")


def test_report_error_with_exception():
    """Test _report_error with exception."""
    downloader = ProjectDownloader(project="test-project")
    downloader._total_files = 10
    downloader._completed_files = 3
    downloader._progress_callback = MagicMock(side_effect=Exception("Callback failed"))
    downloader._error_callback = MagicMock(side_effect=Exception("Error callback failed"))

    # Should not raise exception
    downloader._report_error("Test error")


def test_context_manager_exit_with_exception():
    """Test context manager exit with exception."""
    with patch(
        "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.directory.DDSDirectory"
    ):
        with patch(
            "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.data_getter.DataGetter"
        ):
            with ProjectDownloader(project="test-project") as downloader:
                # Mock cleanup to raise exception
                with patch.object(downloader, "cleanup", side_effect=Exception("Cleanup failed")):
                    # Should not raise exception
                    pass  # Context manager should handle the exception


def test_callback_progress_trigger_cancelled():
    """Test CallbackProgress trigger when cancelled."""
    downloader = ProjectDownloader(project="test-project")
    downloader._cancelled = True
    progress = CallbackProgress(
        progress_callback=MagicMock(),
        file_path="test.txt",
        total_size=1000,
        downloader_instance=downloader,
    )

    progress._trigger_progress_callback()

    # Should not call callback when cancelled
    progress.progress_callback.assert_not_called()


def test_callback_progress_trigger_stop_doing():
    """Test CallbackProgress trigger when stop_doing is True."""
    downloader = ProjectDownloader(project="test-project")
    downloader._getter = MagicMock()
    downloader._getter.stop_doing = True
    progress = CallbackProgress(
        progress_callback=MagicMock(),
        file_path="test.txt",
        total_size=1000,
        downloader_instance=downloader,
    )

    progress._trigger_progress_callback()

    # Should not call callback when stop_doing is True
    progress.progress_callback.assert_not_called()


def test_callback_progress_trigger_first_update():
    """Test CallbackProgress trigger for first update."""
    downloader = ProjectDownloader(project="test-project")
    progress = CallbackProgress(
        progress_callback=MagicMock(),
        file_path="test.txt",
        total_size=1000,
        downloader_instance=downloader,
    )

    # First update should trigger callback
    progress._trigger_progress_callback()

    progress.progress_callback.assert_called_once()


def test_callback_progress_trigger_final_update():
    """Test CallbackProgress trigger for final update."""
    downloader = ProjectDownloader(project="test-project")
    progress = CallbackProgress(
        progress_callback=MagicMock(),
        file_path="test.txt",
        total_size=1000,
        downloader_instance=downloader,
    )
    progress.completed = 1000  # 100% complete

    progress._trigger_progress_callback()

    progress.progress_callback.assert_called_once()


def test_callback_progress_trigger_percentage_change():
    """Test CallbackProgress trigger when percentage changes."""
    downloader = ProjectDownloader(project="test-project")
    progress = CallbackProgress(
        progress_callback=MagicMock(),
        file_path="test.txt",
        total_size=1000,
        downloader_instance=downloader,
    )

    # Set initial state
    progress.completed = 0
    progress._last_callback_time = time.time()
    progress._last_callback_percentage = 0

    # Update to 10% (should trigger callback)
    progress.completed = 100
    progress._trigger_progress_callback()

    progress.progress_callback.assert_called_once()


def test_callback_progress_trigger_time_throttling():
    """Test CallbackProgress trigger with time throttling."""
    downloader = ProjectDownloader(project="test-project")
    progress = CallbackProgress(
        progress_callback=MagicMock(),
        file_path="test.txt",
        total_size=1000,
        downloader_instance=downloader,
    )

    # Set initial state
    progress.completed = 100
    progress._last_callback_time = time.time() - 1.0  # 1 second ago
    progress._last_callback_percentage = 2  # 10%

    # Update to same percentage but enough time has passed
    progress._trigger_progress_callback()

    progress.progress_callback.assert_called_once()


def test_callback_progress_trigger_small_file():
    """Test CallbackProgress trigger for small files."""
    downloader = ProjectDownloader(project="test-project")
    progress = CallbackProgress(
        progress_callback=MagicMock(),
        file_path="test.txt",
        total_size=100,  # Small file
        downloader_instance=downloader,
    )

    # Set initial state
    progress.completed = 0
    progress._last_callback_time = time.time()
    progress._last_callback_percentage = 0

    # Update to 50 bytes (should trigger callback for small files)
    progress.completed = 50
    progress._trigger_progress_callback()

    progress.progress_callback.assert_called_once()


def test_callback_progress_trigger_callback_exception():
    """Test CallbackProgress trigger with callback exception."""
    downloader = ProjectDownloader(project="test-project")
    progress = CallbackProgress(
        progress_callback=MagicMock(side_effect=Exception("Callback failed")),
        file_path="test.txt",
        total_size=1000,
        downloader_instance=downloader,
    )

    # Should not raise exception
    progress._trigger_progress_callback()


def test_callback_progress_init_with_all_parameters():
    """Test CallbackProgress initialization with all parameters."""
    downloader = ProjectDownloader(project="test-project")
    progress = CallbackProgress(
        progress_callback=MagicMock(),
        file_path="test.txt",
        total_size=1000,
        downloader_instance=downloader,
    )

    assert progress.progress_callback is not None
    assert progress.file_path == "test.txt"
    assert progress.total_size == 1000
    assert progress.downloader_instance == downloader
    assert progress.tasks == {}
    assert progress.completed == 0
    assert progress._lock is not None
    assert progress._last_callback_time == 0
    assert progress._callback_throttle == 0.1
    assert progress._last_callback_progress == 0


def test_callback_progress_trigger_with_cancelled_downloader_early_return():
    """Test CallbackProgress trigger early return when downloader is cancelled."""
    downloader = ProjectDownloader(project="test-project")
    downloader._cancelled = True
    progress = CallbackProgress(
        progress_callback=MagicMock(),
        file_path="test.txt",
        total_size=1000,
        downloader_instance=downloader,
    )

    progress._trigger_progress_callback()

    # Should not call callback when cancelled
    progress.progress_callback.assert_not_called()


def test_callback_progress_trigger_with_stop_doing_early_return():
    """Test CallbackProgress trigger early return when stop_doing is True."""
    downloader = ProjectDownloader(project="test-project")
    downloader._getter = MagicMock()
    downloader._getter.stop_doing = True
    progress = CallbackProgress(
        progress_callback=MagicMock(),
        file_path="test.txt",
        total_size=1000,
        downloader_instance=downloader,
    )

    progress._trigger_progress_callback()

    # Should not call callback when stop_doing is True
    progress.progress_callback.assert_not_called()


def test_callback_progress_trigger_progress_calculation_detailed():
    """Test CallbackProgress trigger with detailed progress calculation."""
    downloader = ProjectDownloader(project="test-project")
    downloader._total_files = 10
    downloader._completed_files = 3
    downloader._total_bytes = 10000
    downloader._total_downloaded_bytes = 3000
    downloader._progress_lock = threading.Lock()

    progress = CallbackProgress(
        progress_callback=MagicMock(),
        file_path="test.txt",
        total_size=1000,
        downloader_instance=downloader,
    )
    progress.completed = 500

    progress._trigger_progress_callback()

    # Verify callback was called with correct calculations
    progress.progress_callback.assert_called_once()
    call_args = progress.progress_callback.call_args[0][0]
    assert call_args.current_file == "test.txt"
    assert call_args.total_files == 10
    assert call_args.completed_files == 3
    assert call_args.current_file_progress == 0.5  # 500/1000
    # Overall progress = (3000 + 500) / 10000 = 0.35
    assert call_args.overall_progress == 0.35
    assert call_args.overall_percentage == 35.0


def test_callback_progress_trigger_fallback_calculation_zero_total_bytes():
    """Test CallbackProgress trigger with fallback calculation when total_bytes is 0."""
    downloader = ProjectDownloader(project="test-project")
    downloader._total_files = 5
    downloader._completed_files = 2
    downloader._total_bytes = 0
    downloader._total_downloaded_bytes = 0
    downloader._progress_lock = threading.Lock()

    progress = CallbackProgress(
        progress_callback=MagicMock(),
        file_path="test.txt",
        total_size=1000,
        downloader_instance=downloader,
    )
    progress.completed = 500

    progress._trigger_progress_callback()

    # Verify callback was called with fallback calculation
    progress.progress_callback.assert_called_once()
    call_args = progress.progress_callback.call_args[0][0]
    assert call_args.total_files == 5
    assert call_args.completed_files == 2
    # Fallback calculation: base_progress (2/5) + current_file_contribution (0.5/5) = 0.4 + 0.1 = 0.5
    assert call_args.overall_progress == 0.5
    assert call_args.overall_percentage == 50.0


def test_callback_progress_trigger_small_file_frequent_updates():
    """Test CallbackProgress trigger for small files with frequent updates."""
    downloader = ProjectDownloader(project="test-project")
    downloader._total_files = 1
    downloader._completed_files = 0
    downloader._total_bytes = 0
    downloader._total_downloaded_bytes = 0
    downloader._progress_lock = threading.Lock()

    progress = CallbackProgress(
        progress_callback=MagicMock(),
        file_path="test.txt",
        total_size=500,  # Small file (< 1MB)
        downloader_instance=downloader,
    )

    # Set initial state
    progress.completed = 0
    progress._last_callback_time = time.time()
    progress._last_callback_progress = 0

    # Update to 1KB (should trigger callback for small files)
    progress.completed = 1024
    progress._trigger_progress_callback()

    # Should call callback for small file frequent updates
    progress.progress_callback.assert_called_once()


def test_callback_progress_trigger_progress_percentage_change():
    """Test CallbackProgress trigger when progress percentage changes."""
    downloader = ProjectDownloader(project="test-project")
    downloader._total_files = 1
    downloader._completed_files = 0
    downloader._total_bytes = 0
    downloader._total_downloaded_bytes = 0
    downloader._progress_lock = threading.Lock()

    progress = CallbackProgress(
        progress_callback=MagicMock(),
        file_path="test.txt",
        total_size=1000,
        downloader_instance=downloader,
    )

    # Set initial state
    progress.completed = 0
    progress._last_callback_time = time.time()
    progress._last_callback_progress = 0

    # Update to 10% (should trigger callback due to percentage change)
    progress.completed = 100
    progress._trigger_progress_callback()

    # Should call callback due to percentage change
    progress.progress_callback.assert_called_once()

@pytest.mark.skip("Skipping source conflict test")
def test_initialize_validation_get_all_with_source_conflict(
    mock_data_getter_class, mock_directory_class, mock_data_getter, mock_staging_dir
):
    """Test initialize validation when get_all=True but source is specified."""
    mock_data_getter_class.return_value = mock_data_getter
    mock_directory_class.return_value = mock_staging_dir

    downloader = ProjectDownloader(project="test-project")

    result = downloader.initialize(
        get_all=True,
        source=("file1.txt",),
    )

    assert result is False
    assert not downloader._is_initialized


@patch(
    "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.directory.DDSDirectory"
)
@patch(
    "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.data_getter.DataGetter"
)
def test_initialize_validation_no_source_specified(
    mock_data_getter_class, mock_directory_class, mock_data_getter, mock_staging_dir
):
    """Test initialize validation when get_all=False but no source specified."""
    mock_data_getter_class.return_value = mock_data_getter
    mock_directory_class.return_value = mock_staging_dir

    downloader = ProjectDownloader(project="test-project")

    result = downloader.initialize(
        get_all=False,
        source=(),
        source_path_file=None,
    )

    assert result is False
    assert not downloader._is_initialized


@patch(
    "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.directory.DDSDirectory"
)
@patch(
    "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.data_getter.DataGetter"
)
def test_initialize_custom_destination_path(
    mock_data_getter_class, mock_directory_class, mock_data_getter, mock_staging_dir
):
    """Test initialize with custom destination path."""
    mock_data_getter_class.return_value = mock_data_getter
    mock_directory_class.return_value = mock_staging_dir

    custom_dest = pathlib.Path("/custom/download/path")
    downloader = ProjectDownloader(project="test-project", destination=custom_dest)

    result = downloader.initialize(get_all=True)

    assert result is True
    assert downloader._is_initialized
    # Verify DataGetter was called with custom destination
    mock_data_getter_class.assert_called_once()
    call_args = mock_data_getter_class.call_args
    assert call_args[1]["staging_dir"] is not None


@patch(
    "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.directory.DDSDirectory"
)
@patch(
    "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.data_getter.DataGetter"
)
@patch(
    "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.timestamp.TimeStamp"
)
def test_initialize_default_destination_path(
    mock_timestamp_class,
    mock_data_getter_class,
    mock_directory_class,
    mock_data_getter,
    mock_staging_dir,
):
    """Test initialize with default destination path generation."""
    mock_timestamp = MagicMock()
    mock_timestamp.timestamp = "2025-01-01_12-00-00"
    mock_timestamp_class.return_value = mock_timestamp

    mock_data_getter_class.return_value = mock_data_getter
    mock_directory_class.return_value = mock_staging_dir

    downloader = ProjectDownloader(project="test-project")

    result = downloader.initialize(get_all=True)

    assert result is True
    assert downloader._is_initialized
    # Verify DataGetter was called with generated destination
    mock_data_getter_class.assert_called_once()


@patch(
    "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.directory.DDSDirectory"
)
@patch(
    "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.data_getter.DataGetter"
)
def test_initialize_no_files_to_download(
    mock_data_getter_class, mock_directory_class, mock_staging_dir
):
    """Test initialize when no files are available to download."""
    mock_getter = MagicMock()
    mock_getter.filehandler = MagicMock()
    mock_getter.filehandler.data = {}  # No files
    mock_data_getter_class.return_value = mock_getter
    mock_directory_class.return_value = mock_staging_dir

    downloader = ProjectDownloader(project="test-project")

    result = downloader.initialize(get_all=True)

    assert result is False
    assert not downloader._is_initialized


@patch(
    "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.directory.DDSDirectory"
)
@patch(
    "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.data_getter.DataGetter"
)
def test_initialize_calculates_total_bytes(
    mock_data_getter_class, mock_directory_class, mock_data_getter, mock_staging_dir
):
    """Test initialize calculates total bytes correctly."""
    mock_data_getter_class.return_value = mock_data_getter
    mock_directory_class.return_value = mock_staging_dir

    downloader = ProjectDownloader(project="test-project")

    result = downloader.initialize(get_all=True)

    assert result is True
    assert downloader._is_initialized
    assert downloader._total_files == 3
    assert downloader._total_bytes == 6000  # 1000 + 2000 + 3000
    assert downloader._completed_files == 0
    assert downloader._total_downloaded_bytes == 0


@patch(
    "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.directory.DDSDirectory"
)
@patch(
    "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.data_getter.DataGetter"
)
def test_initialize_with_all_parameters(
    mock_data_getter_class, mock_directory_class, mock_data_getter, mock_staging_dir
):
    """Test initialize with all optional parameters."""
    mock_data_getter_class.return_value = mock_data_getter
    mock_directory_class.return_value = mock_staging_dir

    downloader = ProjectDownloader(project="test-project")

    result = downloader.initialize(
        get_all=True,
        break_on_fail=True,
        verify_checksum=True,
    )

    assert result is True
    assert downloader._is_initialized
    # Verify DataGetter was called with all parameters
    mock_data_getter_class.assert_called_once()
    call_args = mock_data_getter_class.call_args
    assert call_args[1]["break_on_fail"] is True
    assert call_args[1]["verify_checksum"] is True
    assert call_args[1]["silent"] is True


@patch(
    "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.directory.DDSDirectory"
)
@patch(
    "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.data_getter.DataGetter"
)
def test_download_all_stop_doing_before_start(
    mock_data_getter_class, mock_directory_class, mock_data_getter, mock_staging_dir
):
    """Test download_all when stop_doing is True before starting."""
    mock_data_getter.stop_doing = True  # Set stop_doing before starting
    mock_data_getter_class.return_value = mock_data_getter
    mock_directory_class.return_value = mock_staging_dir

    downloader = ProjectDownloader(project="test-project")
    downloader.initialize(get_all=True)

    result = downloader.download_all()

    assert result is False
    assert downloader._is_downloading is False


@patch(
    "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.directory.DDSDirectory"
)
@patch(
    "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.data_getter.DataGetter"
)
def test_download_all_cancellation_during_execution(
    mock_data_getter_class, mock_directory_class, mock_data_getter, mock_staging_dir
):
    """Test download_all with cancellation during execution."""
    mock_data_getter.download_and_verify.return_value = (True, "Success")
    mock_data_getter.stop_doing = False
    mock_data_getter_class.return_value = mock_data_getter
    mock_directory_class.return_value = mock_staging_dir

    downloader = ProjectDownloader(project="test-project")
    downloader.initialize(get_all=True)

    # Cancel during execution
    def mock_submit(func, *args, **kwargs):
        downloader._cancelled = True
        return MagicMock()

    with patch("concurrent.futures.ThreadPoolExecutor.submit", side_effect=mock_submit):
        result = downloader.download_all(num_threads=1)

    assert result is False


@patch(
    "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.directory.DDSDirectory"
)
@patch(
    "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.data_getter.DataGetter"
)
def test_download_all_future_cancelled(
    mock_data_getter_class, mock_directory_class, mock_data_getter, mock_staging_dir
):
    """Test download_all when future is cancelled."""
    mock_data_getter_class.return_value = mock_data_getter
    mock_directory_class.return_value = mock_staging_dir

    downloader = ProjectDownloader(project="test-project")
    downloader.initialize(get_all=True)

    # Create a cancelled future
    cancelled_future = MagicMock()
    cancelled_future.cancelled.return_value = True

    with patch("concurrent.futures.ThreadPoolExecutor") as mock_executor_class:
        mock_executor = MagicMock()
        mock_executor_class.return_value.__enter__.return_value = mock_executor
        mock_executor.submit.return_value = cancelled_future

        # Mock wait to return the cancelled future
        with patch("concurrent.futures.wait") as mock_wait:
            mock_wait.return_value = ([cancelled_future], [])

            result = downloader.download_all(num_threads=1)

            # Should handle cancelled future gracefully
            assert result is False

@pytest.mark.skip("Skipping future exception test")
@patch(
    "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.directory.DDSDirectory"
)
@patch(
    "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.data_getter.DataGetter"
)
def test_download_all_future_exception(
    mock_data_getter_class, mock_directory_class, mock_data_getter, mock_staging_dir
):
    """Test download_all when future raises exception."""
    mock_data_getter_class.return_value = mock_data_getter
    mock_directory_class.return_value = mock_staging_dir

    downloader = ProjectDownloader(project="test-project")
    downloader.initialize(get_all=True)

    # Create a future that raises exception
    exception_future = MagicMock()
    exception_future.cancelled.return_value = False
    exception_future.result.side_effect = dds_cli.exceptions.DownloadError("Download failed")

    with patch("concurrent.futures.ThreadPoolExecutor") as mock_executor_class:
        mock_executor = MagicMock()
        mock_executor_class.return_value.__enter__.return_value = mock_executor
        mock_executor.submit.return_value = exception_future

        # Mock wait to return the exception future
        with patch("concurrent.futures.wait") as mock_wait:
            mock_wait.return_value = ([exception_future], [])

            with patch.object(downloader, "_report_error") as mock_report_error:
                result = downloader.download_all(num_threads=1)

                # Should handle exception gracefully and return False
                assert result is False
                mock_report_error.assert_called()


@patch(
    "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.directory.DDSDirectory"
)
@patch(
    "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.data_getter.DataGetter"
)
def test_download_all_non_tuple_result(
    mock_data_getter_class, mock_directory_class, mock_data_getter, mock_staging_dir
):
    """Test download_all when download_and_verify returns non-tuple result."""
    mock_data_getter.download_and_verify.return_value = True  # Non-tuple result
    mock_data_getter.stop_doing = False
    mock_data_getter_class.return_value = mock_data_getter
    mock_directory_class.return_value = mock_staging_dir

    downloader = ProjectDownloader(project="test-project")
    downloader.initialize(get_all=True)

    result = downloader.download_all(num_threads=1)

    assert result is True


@patch(
    "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.directory.DDSDirectory"
)
@pytest.mark.skip("Skipping timeout error test")
@patch(
    "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.data_getter.DataGetter"
)
def test_download_all_timeout_error(
    mock_data_getter_class, mock_directory_class, mock_data_getter, mock_staging_dir
):
    """Test download_all with timeout error."""
    mock_data_getter.stop_doing = False
    mock_data_getter_class.return_value = mock_data_getter
    mock_directory_class.return_value = mock_staging_dir

    downloader = ProjectDownloader(project="test-project")
    downloader.initialize(get_all=True)

    with patch("concurrent.futures.ThreadPoolExecutor") as mock_executor_class:
        mock_executor = MagicMock()
        mock_executor_class.return_value.__enter__.return_value = mock_executor
        mock_executor.submit.return_value = MagicMock()

        # Mock wait to raise timeout error
        with patch("concurrent.futures.wait") as mock_wait:
            mock_wait.side_effect = concurrent.futures.TimeoutError()

            result = downloader.download_all(num_threads=1)

            # Should handle timeout gracefully
            assert result is False

@pytest.mark.skip("Skipping general exception test")
@patch(
    "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.directory.DDSDirectory"
)
@patch(
    "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.dds_cli.data_getter.DataGetter"
)
def test_download_all_general_exception(
    mock_data_getter_class, mock_directory_class, mock_data_getter, mock_staging_dir
):
    """Test download_all with general exception."""
    mock_data_getter_class.return_value = mock_data_getter
    mock_directory_class.return_value = mock_staging_dir

    downloader = ProjectDownloader(project="test-project")
    downloader.initialize(get_all=True)

    with patch("concurrent.futures.ThreadPoolExecutor") as mock_executor_class:
        mock_executor_class.side_effect = RuntimeError("Executor failed")

        with patch.object(downloader, "_report_error") as mock_report_error:
            result = downloader.download_all(num_threads=1)

            # Should handle exception gracefully
            mock_report_error.assert_called()
            assert result is False

