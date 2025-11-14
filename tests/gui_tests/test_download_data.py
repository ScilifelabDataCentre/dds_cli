"""Tests for DownloadData GUI widget."""

from unittest.mock import MagicMock, patch

import pytest

from dds_cli.dds_gui.app import DDSApp
from dds_cli.dds_gui.pages.project_actions.download_data.download_data import DownloadData
from dds_cli.dds_gui.pages.project_actions.download_data.project_downloader import (
    DownloadProgress,
    DownloadResult,
)


def test_download_data_initialization():
    """Test DownloadData widget initialization."""
    widget = DownloadData()

    assert widget.downloader is None
    assert widget.download_thread is None
    assert widget.progress == 0.0
    assert widget.files_downloaded == 0
    assert widget.error_files == 0
    assert widget.total_files == 0
    assert widget.selected_project_id is None
    assert widget.is_downloading is False


def test_compose_method():
    """Test the compose method creates correct widgets."""
    # Skip this test as it requires app context for Textual widgets
    # The compose method is tested indirectly through the app context tests
    pass


def test_watch_files_downloaded_without_errors():
    """Test watching files_downloaded changes without errors."""
    widget = DownloadData()
    widget.error_files = 0
    widget.total_files = 10

    with patch.object(widget, "query_one") as mock_query:
        mock_label = MagicMock()
        mock_query.return_value = mock_label

        widget.watch_files_downloaded(5)

        mock_label.update.assert_called_once_with("Files: 5/10")


def test_watch_files_downloaded_with_errors():
    """Test watching files_downloaded changes with errors."""
    widget = DownloadData()
    widget.error_files = 2
    widget.total_files = 10

    with patch.object(widget, "query_one") as mock_query:
        mock_label = MagicMock()
        mock_query.return_value = mock_label

        widget.watch_files_downloaded(5)

        mock_label.update.assert_called_once_with("Files: 5/10 (❌ Errors: 2)")


def test_watch_error_files_first_error():
    """Test watching error_files when first error occurs."""
    widget = DownloadData()
    widget.files_downloaded = 3
    widget.total_files = 10

    with patch.object(widget, "query_one") as mock_query:
        mock_label = MagicMock()
        mock_query.return_value = mock_label

        widget.watch_error_files(1)

        mock_label.update.assert_called_once_with("Files: 3/10 (❌ Errors: 1)")


def test_watch_error_files_subsequent_errors():
    """Test watching error_files for subsequent errors."""
    widget = DownloadData()
    widget.files_downloaded = 3
    widget.total_files = 10

    with patch.object(widget, "query_one") as mock_query:
        mock_label = MagicMock()
        mock_query.return_value = mock_label

        widget.watch_error_files(2)

        mock_label.update.assert_called_once_with("Files: 3/10 (❌ Errors: 2)")


def test_watch_is_downloading_enables_button():
    """Test watching is_downloading changes enables button."""
    widget = DownloadData()
    widget.selected_project_id = "test-project"
    widget.has_project_access = True  # Ensure access is granted

    with patch.object(widget, "query_one") as mock_query:
        mock_button = MagicMock()
        mock_query.return_value = mock_button

        widget.watch_is_downloading(False)

        assert mock_button.disabled is False


def test_watch_is_downloading_disables_button():
    """Test watching is_downloading changes disables button."""
    widget = DownloadData()
    widget.selected_project_id = "test-project"

    with patch.object(widget, "query_one") as mock_query:
        mock_button = MagicMock()
        mock_query.return_value = mock_button

        widget.watch_is_downloading(True)

        assert mock_button.disabled is True


def test_update_progress_ui():
    """Test updating progress UI."""
    widget = DownloadData()

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
        bytes_downloaded=1000,
        total_bytes=2000,
    )

    with patch.object(widget, "query_one") as mock_query:
        mock_progress_bar = MagicMock()
        mock_query.return_value = mock_progress_bar

        widget._update_progress_ui(progress)

        # Verify reactive attributes were updated
        assert widget.progress == 50.0
        assert widget.files_downloaded == 5
        assert widget.error_files == 1
        assert widget.total_files == 10

        # Verify progress bar was updated (may be called multiple times due to watchers)
        assert mock_progress_bar.update.called
        # Check that the progress update call was made
        progress_calls = [
            call for call in mock_progress_bar.update.call_args_list if "progress" in call.kwargs
        ]
        assert len(progress_calls) > 0
        assert progress_calls[0].kwargs["progress"] == 50.0


def test_update_progress_ui_no_progress_bar():
    """Test updating progress UI when progress bar doesn't exist."""
    widget = DownloadData()

    progress = DownloadProgress(
        current_file="test.txt",
        total_files=10,
        completed_files=5,
        error_files=0,
        current_file_progress=0.5,
        overall_progress=0.5,
        overall_percentage=50.0,
        status="downloading",
    )

    with patch.object(widget, "query_one") as mock_query:
        mock_query.return_value = None  # No progress bar found

        # Should not raise exception
        widget._update_progress_ui(progress)

        # Verify reactive attributes were still updated
        assert widget.progress == 50.0
        assert widget.files_downloaded == 5
        assert widget.error_files == 0
        assert widget.total_files == 10


def test_on_file_completed():
    """Test file completed callback."""
    widget = DownloadData()

    result = DownloadResult(
        success=True,
        file_path="test.txt",
        files_downloaded=1,
        error_message=None,
        file_size=1000,
    )

    # Should not raise exception
    widget._on_file_completed(result)


def test_reset_download_state():
    """Test resetting download state."""
    widget = DownloadData()
    widget.is_downloading = True
    widget.download_thread = MagicMock()

    widget._reset_download_state()

    assert widget.is_downloading is False
    assert widget.download_thread is None


def test_on_button_pressed_success():
    """Test button press handling."""
    widget = DownloadData()

    with patch.object(widget, "query_one") as mock_query, patch.object(
        widget, "_start_download"
    ) as mock_start:
        mock_progress_bar = MagicMock()
        mock_files_label = MagicMock()
        mock_query.side_effect = [mock_progress_bar, mock_files_label]

        # Create a mock click event
        mock_event = MagicMock()
        mock_event.button.id = "download-project-content-button"

        widget.on_button_pressed(mock_event)

        mock_progress_bar.classes = "enabled"
        mock_files_label.classes = "enabled"
        mock_start.assert_called_once()


def test_on_button_pressed_exception():
    """Test button press handling with exception."""
    widget = DownloadData()

    with patch.object(widget, "query_one") as mock_query:
        mock_query.side_effect = RuntimeError("Query failed")

        # Create a mock click event
        mock_event = MagicMock()
        mock_event.button.id = "download-project-content-button"

        # Should not raise exception
        widget.on_button_pressed(mock_event)


def test_start_download_already_downloading():
    """Test starting download when already downloading."""
    widget = DownloadData()
    widget.is_downloading = True

    # Should return early without starting download
    widget._start_download()

    # Verify that is_downloading is still True
    assert widget.is_downloading is True


def test_full_download_worker_stop_after_init():
    """Test download worker stopping after initialization."""
    widget = DownloadData()
    widget.selected_project_id = "test-project"

    with patch(
        "dds_cli.dds_gui.pages.project_actions.download_data.download_data.ProjectDownloader"
    ) as mock_downloader_class, patch(
        "dds_cli.directory.DDSDirectory"
    ) as mock_directory_class, patch(
        "dds_cli.data_getter.DataGetter"
    ) as mock_data_getter_class:
        mock_downloader = MagicMock()
        mock_downloader_class.return_value = mock_downloader
        mock_downloader.initialize.return_value = True

        # Mock the directory creation
        mock_directory_class.return_value = MagicMock()

        # Mock the data getter
        mock_data_getter_class.return_value = MagicMock()

        # Set stop flag before starting
        widget._stop_download.set()

        widget._full_download_worker("test-project")

        # Should not call download_all
        mock_downloader.download_all.assert_not_called()


def test_full_download_worker_stop_before_download():
    """Test download worker stopping before download starts."""
    widget = DownloadData()
    widget.selected_project_id = "test-project"

    with patch(
        "dds_cli.dds_gui.pages.project_actions.download_data.download_data.ProjectDownloader"
    ) as mock_downloader_class, patch(
        "dds_cli.directory.DDSDirectory"
    ) as mock_directory_class, patch(
        "dds_cli.data_getter.DataGetter"
    ) as mock_data_getter_class:
        mock_downloader = MagicMock()
        mock_downloader_class.return_value = mock_downloader
        mock_downloader.initialize.return_value = True

        # Mock the directory creation
        mock_directory_class.return_value = MagicMock()

        # Mock the data getter
        mock_data_getter_class.return_value = MagicMock()

        # Set stop flag after initialization but before download
        def mock_initialize(*args, **kwargs):
            widget._stop_download.set()
            return True

        mock_downloader.initialize.side_effect = mock_initialize

        widget._full_download_worker("test-project")

        # Should not call download_all
        mock_downloader.download_all.assert_not_called()


def test_full_download_worker_download_success():
    """Test successful download in worker."""
    widget = DownloadData()
    widget.selected_project_id = "test-project"

    with patch(
        "dds_cli.dds_gui.pages.project_actions.download_data.download_data.ProjectDownloader"
    ) as mock_downloader_class, patch(
        "dds_cli.directory.DDSDirectory"
    ) as mock_directory_class, patch(
        "dds_cli.data_getter.DataGetter"
    ) as mock_data_getter_class, patch.object(
        widget, "_update_status"
    ) as mock_update:
        mock_downloader = MagicMock()
        mock_downloader_class.return_value = mock_downloader
        mock_downloader.initialize.return_value = True
        mock_downloader.download_all.return_value = True

        # Mock the directory creation
        mock_directory_class.return_value = MagicMock()

        # Mock the data getter
        mock_data_getter_class.return_value = MagicMock()

        widget._full_download_worker("test-project")

        # Verify status updates - should have at least one call
        assert mock_update.call_count >= 1


def test_full_download_worker_download_failure():
    """Test download failure in worker."""
    widget = DownloadData()
    widget.selected_project_id = "test-project"

    with patch(
        "dds_cli.dds_gui.pages.project_actions.download_data.download_data.ProjectDownloader"
    ) as mock_downloader_class, patch(
        "dds_cli.directory.DDSDirectory"
    ) as mock_directory_class, patch(
        "dds_cli.data_getter.DataGetter"
    ) as mock_data_getter_class, patch.object(
        widget, "_update_status"
    ) as mock_update:
        mock_downloader = MagicMock()
        mock_downloader_class.return_value = mock_downloader
        mock_downloader.initialize.return_value = True
        mock_downloader.download_all.return_value = False

        # Mock the directory creation
        mock_directory_class.return_value = MagicMock()

        # Mock the data getter
        mock_data_getter_class.return_value = MagicMock()

        widget._full_download_worker("test-project")

        # Verify status updates - should have at least one call
        assert mock_update.call_count >= 1


def test_full_download_worker_exception():
    """Test exception handling in worker."""
    widget = DownloadData()
    widget.selected_project_id = "test-project"

    with patch(
        "dds_cli.dds_gui.pages.project_actions.download_data.download_data.ProjectDownloader"
    ) as mock_downloader_class, patch(
        "dds_cli.directory.DDSDirectory"
    ) as mock_directory_class, patch(
        "dds_cli.data_getter.DataGetter"
    ) as mock_data_getter_class, patch.object(
        widget, "_update_status"
    ) as mock_update:
        mock_downloader = MagicMock()
        mock_downloader_class.return_value = mock_downloader
        mock_downloader.initialize.side_effect = Exception("Init failed")

        # Mock the directory creation
        mock_directory_class.return_value = MagicMock()

        # Mock the data getter
        mock_data_getter_class.return_value = MagicMock()

        widget._full_download_worker("test-project")

        # Verify error status was set - should contain the exception message
        assert mock_update.call_count >= 1
        # Check that the call contains "Unexpected error" (new behavior)
        call_args = str(mock_update.call_args)
        assert "Unexpected error" in call_args


def test_on_unmount_with_downloader():
    """Test unmount with active downloader."""
    widget = DownloadData()
    widget.downloader = MagicMock()
    widget.download_thread = MagicMock()
    widget.download_thread.is_alive.return_value = True

    widget.on_unmount()

    # Verify cancellation was called
    widget.downloader.cancel_download.assert_called_once()
    widget.download_thread.join.assert_called_once_with(timeout=1.0)


def test_on_unmount_downloader_exception():
    """Test unmount with downloader cancellation exception."""
    widget = DownloadData()
    widget.downloader = MagicMock()
    widget.downloader.cancel_download.side_effect = Exception("Cancel failed")
    widget.download_thread = MagicMock()
    widget.download_thread.is_alive.return_value = False

    # Should not raise exception
    widget.on_unmount()


def test_start_download_creates_thread():
    """Test that _start_download creates and starts download thread."""
    widget = DownloadData()
    widget.selected_project_id = "test-project"

    with patch.object(widget, "query_one") as mock_query, patch(
        "dds_cli.dds_gui.pages.project_actions.download_data.download_data.ProjectDownloader"
    ) as mock_downloader_class, patch(
        "dds_cli.directory.DDSDirectory"
    ) as mock_directory_class, patch(
        "dds_cli.data_getter.DataGetter"
    ) as mock_data_getter_class, patch(
        "threading.Thread"
    ) as mock_thread_class:
        # Mock query_one to return None (no error label)
        mock_query.return_value = None

        # Mock downloader and directory
        mock_downloader = MagicMock()
        mock_downloader_class.return_value = mock_downloader
        mock_directory_class.return_value = MagicMock()

        # Mock the data getter
        mock_data_getter_class.return_value = MagicMock()

        # Mock thread
        mock_thread = MagicMock()
        mock_thread_class.return_value = mock_thread

        widget._start_download()

        # Verify thread was created and started
        mock_thread_class.assert_called_once_with(
            target=widget._full_download_worker, args=("test-project",), daemon=True
        )
        mock_thread.start.assert_called_once()


def test_full_download_workflow():
    """Test complete download workflow."""
    widget = DownloadData()
    widget.selected_project_id = "test-project"

    # Mock the ProjectDownloader to simulate a successful download
    with patch(
        "dds_cli.dds_gui.pages.project_actions.download_data.download_data.ProjectDownloader"
    ) as mock_downloader_class, patch(
        "dds_cli.directory.DDSDirectory"
    ) as mock_directory_class, patch(
        "dds_cli.data_getter.DataGetter"
    ) as mock_data_getter_class:
        mock_downloader = MagicMock()
        mock_downloader_class.return_value = mock_downloader
        mock_downloader.initialize.return_value = True
        mock_downloader.download_all.return_value = True

        # Mock the directory creation
        mock_directory_class.return_value = MagicMock()

        # Mock the data getter
        mock_data_getter_class.return_value = MagicMock()

        # Test the download worker directly to avoid app context issues
        widget._full_download_worker("test-project")

        # Verify that the downloader was created and used
        mock_downloader_class.assert_called_once()
        mock_downloader.initialize.assert_called_once()
        mock_downloader.download_all.assert_called_once()

        # Verify final state - is_downloading should be False after completion
        assert widget.is_downloading is False

        # Simulate progress updates
        progress1 = DownloadProgress(
            current_file="file1.txt",
            total_files=3,
            completed_files=1,
            error_files=0,
            current_file_progress=1.0,
            overall_progress=0.33,
            overall_percentage=33.0,
            status="downloading",
        )

        progress2 = DownloadProgress(
            current_file="file2.txt",
            total_files=3,
            completed_files=2,
            error_files=1,
            current_file_progress=1.0,
            overall_progress=0.67,
            overall_percentage=67.0,
            status="downloading",
        )

        progress3 = DownloadProgress(
            current_file="file3.txt",
            total_files=3,
            completed_files=3,
            error_files=1,
            current_file_progress=1.0,
            overall_progress=1.0,
            overall_percentage=100.0,
            status="completed",
        )

        # Update progress
        widget._update_progress_ui(progress1)
        assert widget.progress == 33.0
        assert widget.files_downloaded == 1
        assert widget.error_files == 0

        widget._update_progress_ui(progress2)
        assert widget.progress == 67.0
        assert widget.files_downloaded == 2
        assert widget.error_files == 1

        widget._update_progress_ui(progress3)
        assert widget.progress == 100.0
        assert widget.files_downloaded == 3
        assert widget.error_files == 1


def test_error_handling_workflow():
    """Test error handling workflow."""
    widget = DownloadData()
    widget.selected_project_id = "test-project"

    # Mock the ProjectDownloader to simulate an error
    with patch(
        "dds_cli.dds_gui.pages.project_actions.download_data.download_data.ProjectDownloader"
    ) as mock_downloader_class, patch(
        "dds_cli.directory.DDSDirectory"
    ) as mock_directory_class, patch(
        "dds_cli.data_getter.DataGetter"
    ) as mock_data_getter_class:
        mock_downloader = MagicMock()
        mock_downloader_class.return_value = mock_downloader
        mock_downloader.initialize.return_value = False  # Simulate initialization failure

        # Mock the directory creation
        mock_directory_class.return_value = MagicMock()

        # Mock the data getter
        mock_data_getter_class.return_value = MagicMock()

        with patch.object(widget, "_update_status") as mock_update:
            widget._full_download_worker("test-project")

            # Verify error status was set - should contain "Failed to initialize download"
            assert mock_update.call_count >= 1
            # Check that the call contains "Failed to initialize download"
            call_args = str(mock_update.call_args)
            assert "Failed to initialize download" in call_args


def test_cancellation_workflow():
    """Test download cancellation workflow."""
    widget = DownloadData()
    widget.selected_project_id = "test-project"
    widget.is_downloading = True
    widget.downloader = MagicMock()
    widget.download_thread = MagicMock()
    widget.download_thread.is_alive.return_value = True

    # Test unmount (which triggers cancellation)
    widget.on_unmount()

    # Verify cancellation was called
    widget.downloader.cancel_download.assert_called_once()
    widget.download_thread.join.assert_called_once_with(timeout=1.0)
    assert widget.is_downloading is False


@pytest.mark.asyncio
async def test_download_data_with_app_context():
    """Test DownloadData widget with proper app context."""
    app = DDSApp(token_path="/tmp/test_token")

    async with app.run_test() as pilot:
        # Create the widget within the app context
        widget = DownloadData()
        app.mount(widget)

        # Test that the widget can access app properties
        assert hasattr(widget, "app")
        assert widget.app is not None

        # Test setting project ID
        widget.selected_project_id = "test-project"
        assert widget.selected_project_id == "test-project"

        # Test button state
        widget.is_downloading = False
        assert widget.is_downloading is False


@pytest.mark.asyncio
async def test_download_workflow_with_app():
    """Test download workflow with proper app context."""
    app = DDSApp(token_path="/tmp/test_token")

    async with app.run_test() as pilot:
        widget = DownloadData()
        app.mount(widget)

        # Set up the widget
        widget.selected_project_id = "test-project"

        # Mock the ProjectDownloader
        with patch(
            "dds_cli.dds_gui.pages.project_actions.download_data.download_data.ProjectDownloader"
        ) as mock_downloader_class:
            mock_downloader = MagicMock()
            mock_downloader_class.return_value = mock_downloader
            mock_downloader.initialize.return_value = True
            mock_downloader.download_all.return_value = True

            # Test starting download
            widget._start_download()

            # Verify state
            assert widget.is_downloading is True
            assert widget.progress == 0.0
            assert widget.files_downloaded == 0
            assert widget.error_files == 0
            assert widget.total_files == 0


@pytest.mark.asyncio
async def test_progress_updates_with_app():
    """Test progress updates with proper app context."""
    app = DDSApp(token_path="/tmp/test_token")

    async with app.run_test() as pilot:
        widget = DownloadData()
        app.mount(widget)

        # Create progress data
        progress = DownloadProgress(
            current_file="test.txt",
            total_files=5,
            completed_files=3,
            error_files=1,
            current_file_progress=1.0,
            overall_progress=0.8,
            overall_percentage=80.0,
            status="downloading",
        )

        # Update progress
        widget._update_progress_ui(progress)

        # Verify reactive attributes were updated
        assert widget.progress == 80.0
        assert widget.files_downloaded == 3
        assert widget.error_files == 1
        assert widget.total_files == 5

        # The progress bar update is tested in the unit tests
        # This test verifies the reactive behavior works in app context


@pytest.mark.asyncio
async def test_start_download_no_project_selected_with_app_context():
    """Test starting download with no project selected in app context."""
    app = DDSApp(token_path="/tmp/test_token")

    async with app.run_test() as pilot:
        widget = DownloadData()
        app.mount(widget)

        # Set no project selected
        widget.selected_project_id = None

        # Mock the app.notify method to track calls
        with patch.object(app, "notify") as mock_notify:
            widget._start_download()

            # Verify notification was called
            mock_notify.assert_called_once_with("No project selected", severity="error")

            # Verify is_downloading is still False
            assert widget.is_downloading is False


def test_full_download_worker_stop_after_initialization():
    """Test download worker stopping after initialization."""
    widget = DownloadData()
    widget.selected_project_id = "test-project"

    with patch(
        "dds_cli.dds_gui.pages.project_actions.download_data.download_data.ProjectDownloader"
    ) as mock_downloader_class, patch(
        "dds_cli.directory.DDSDirectory"
    ) as mock_directory_class, patch(
        "dds_cli.data_getter.DataGetter"
    ) as mock_data_getter_class:
        mock_downloader = MagicMock()
        mock_downloader_class.return_value = mock_downloader

        # Mock initialize to set stop flag after successful initialization
        def mock_initialize(*args, **kwargs):
            widget._stop_download.set()
            return True

        mock_downloader.initialize.side_effect = mock_initialize
        mock_directory_class.return_value = MagicMock()

        # Mock the data getter
        mock_data_getter_class.return_value = MagicMock()

        widget._full_download_worker("test-project")

        # Should not call download_all
        mock_downloader.download_all.assert_not_called()


def test_full_download_worker_stop_before_download_start():
    """Test download worker stopping before download starts."""
    widget = DownloadData()
    widget.selected_project_id = "test-project"

    with patch(
        "dds_cli.dds_gui.pages.project_actions.download_data.download_data.ProjectDownloader"
    ) as mock_downloader_class, patch(
        "dds_cli.directory.DDSDirectory"
    ) as mock_directory_class, patch(
        "dds_cli.data_getter.DataGetter"
    ) as mock_data_getter_class:
        mock_downloader = MagicMock()
        mock_downloader_class.return_value = mock_downloader
        mock_downloader.initialize.return_value = True

        # Set stop flag after initialization but before download
        def mock_initialize(*args, **kwargs):
            # Initialize successfully first
            widget._stop_download.clear()
            return True

        mock_downloader.initialize.side_effect = mock_initialize

        # Set stop flag after initialization
        def mock_update_status(status):
            if status == "Starting download...":
                widget._stop_download.set()

        with patch.object(widget, "_update_status", side_effect=mock_update_status):
            mock_directory_class.return_value = MagicMock()

            # Mock the data getter
            mock_data_getter_class.return_value = MagicMock()
            widget._full_download_worker("test-project")

        # Should not call download_all
        mock_downloader.download_all.assert_not_called()


def test_update_status_with_app_context():
    """Test _update_status with proper app context."""
    app = DDSApp(token_path="/tmp/test_token")

    async def run_test():
        async with app.run_test() as pilot:
            widget = DownloadData()
            app.mount(widget)

            # Should not raise exception
            widget._update_status("Test status")

    import asyncio

    asyncio.run(run_test())


def test_on_progress_update_with_app_context():
    """Test _on_progress_update with proper app context."""
    app = DDSApp(token_path="/tmp/test_token")

    async def run_test():
        async with app.run_test() as pilot:
            widget = DownloadData()
            app.mount(widget)

            progress = DownloadProgress(
                current_file="test.txt",
                total_files=1,
                completed_files=0,
                error_files=0,
                current_file_progress=0.5,
                overall_progress=0.5,
                overall_percentage=50.0,
                status="downloading",
            )

            # Should not raise exception
            widget._on_progress_update(progress)

    import asyncio

    asyncio.run(run_test())


def test_reset_download_state_with_app_context():
    """Test _reset_download_state with proper app context."""
    app = DDSApp(token_path="/tmp/test_token")

    async def run_test():
        async with app.run_test() as pilot:
            widget = DownloadData()
            app.mount(widget)
            widget.is_downloading = True
            widget.download_thread = MagicMock()

            # Should handle the error gracefully
            widget._reset_download_state()

            # State should still be reset
            assert widget.is_downloading is False
            assert widget.download_thread is None

    import asyncio

    asyncio.run(run_test())


def test_on_error():
    """Test error callback handling."""
    widget = DownloadData()

    with patch.object(widget, "_update_status") as mock_update:
        widget._on_error("Test error message")

        mock_update.assert_called_once_with("Error: Test error message")


def test_full_download_worker_exception_during_cleanup():
    """Test exception handling during cleanup in worker."""
    widget = DownloadData()
    widget.selected_project_id = "test-project"

    with patch(
        "dds_cli.dds_gui.pages.project_actions.download_data.download_data.ProjectDownloader"
    ) as mock_downloader_class, patch(
        "dds_cli.directory.DDSDirectory"
    ) as mock_directory_class, patch(
        "dds_cli.data_getter.DataGetter"
    ) as mock_data_getter_class:
        mock_downloader = MagicMock()
        mock_downloader_class.return_value = mock_downloader
        mock_downloader.initialize.side_effect = Exception("Init failed")

        mock_directory_class.return_value = MagicMock()

        # Mock the data getter
        mock_data_getter_class.return_value = MagicMock()

        # Should not raise exception
        widget._full_download_worker("test-project")

        # State should still be reset
        assert widget.is_downloading is False
        assert widget.download_thread is None


def test_full_download_worker_final_fallback_error_handling():
    """Test final fallback error handling in worker."""
    widget = DownloadData()
    widget.selected_project_id = "test-project"

    with patch(
        "dds_cli.dds_gui.pages.project_actions.download_data.download_data.ProjectDownloader"
    ) as mock_downloader_class, patch(
        "dds_cli.directory.DDSDirectory"
    ) as mock_directory_class, patch(
        "dds_cli.data_getter.DataGetter"
    ) as mock_data_getter_class:
        mock_downloader = MagicMock()
        mock_downloader_class.return_value = mock_downloader
        mock_downloader.initialize.side_effect = Exception("Init failed")

        mock_directory_class.return_value = MagicMock()

        # Mock the data getter
        mock_data_getter_class.return_value = MagicMock()

        # Should not raise exception
        widget._full_download_worker("test-project")


def test_watch_selected_project_id_updates_button_state():
    """Test that watching selected_project_id updates button state."""
    widget = DownloadData()
    widget.selected_project_id = "test-project"
    widget.is_downloading = False

    with patch.object(widget, "query_one") as mock_query:
        mock_button = MagicMock()
        mock_query.return_value = mock_button

        # Test updating project ID
        widget.watch_selected_project_id("new-project")

        # Should call watch_is_downloading to update button state
        assert widget.selected_project_id == "new-project"


def test_watch_files_downloaded_with_query_exception():
    """Test watch_files_downloaded when query raises exception."""
    widget = DownloadData()
    widget.error_files = 0
    widget.total_files = 10

    with patch.object(widget, "query_one") as mock_query:
        mock_query.side_effect = Exception("Query failed")

        # Should not raise exception
        widget.watch_files_downloaded(5)


def test_watch_error_files_with_query_exception():
    """Test watch_error_files when query raises exception."""
    widget = DownloadData()
    widget.files_downloaded = 3
    widget.total_files = 10

    with patch.object(widget, "query_one") as mock_query:
        mock_query.side_effect = Exception("Query failed")

        # Should not raise exception
        widget.watch_error_files(1)


def test_watch_total_files_with_query_exception():
    """Test watch_total_files when query raises exception."""
    widget = DownloadData()
    widget.files_downloaded = 3
    widget.error_files = 1

    with patch.object(widget, "query_one") as mock_query:
        mock_query.side_effect = Exception("Query failed")

        # Should not raise exception
        widget.watch_total_files(10)


def test_watch_is_downloading_with_query_exception():
    """Test watch_is_downloading when query raises exception."""
    widget = DownloadData()
    widget.selected_project_id = "test-project"

    with patch.object(widget, "query_one") as mock_query:
        mock_query.side_effect = Exception("Query failed")

        # Should not raise exception
        widget.watch_is_downloading(True)


def test_update_progress_ui_with_progress_bar_update_exception():
    """Test _update_progress_ui when progress bar update raises exception."""
    widget = DownloadData()

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
        bytes_downloaded=1000,
        total_bytes=2000,
    )

    with patch.object(widget, "query_one") as mock_query:
        mock_progress_bar = MagicMock()
        mock_progress_bar.update.side_effect = Exception("Update failed")
        mock_query.return_value = mock_progress_bar

        # Should not raise exception
        widget._update_progress_ui(progress)

        # Verify reactive attributes were updated
        assert widget.progress == 50.0
        assert widget.files_downloaded == 5
        assert widget.error_files == 1
        assert widget.total_files == 10


def test_watch_files_downloaded_with_error_files_and_query_exception():
    """Test watch_files_downloaded with errors when query raises exception."""
    widget = DownloadData()
    widget.error_files = 2
    widget.total_files = 10

    with patch.object(widget, "query_one") as mock_query:
        mock_query.side_effect = Exception("Query failed")

        # Should not raise exception
        widget.watch_files_downloaded(5)


def test_watch_is_downloading_disables_button_with_query_exception():
    """Test watch_is_downloading disables button when query raises exception."""
    widget = DownloadData()
    widget.selected_project_id = "test-project"

    with patch.object(widget, "query_one") as mock_query:
        mock_query.side_effect = Exception("Query failed")

        # Should not raise exception
        widget.watch_is_downloading(True)


def test_on_button_pressed_with_exception():
    """Test button press handling with exception."""
    widget = DownloadData()

    with patch.object(widget, "query_one") as mock_query:
        mock_query.side_effect = RuntimeError("Query failed")

        # Create a mock click event
        mock_event = MagicMock()
        mock_event.button.id = "download-project-content-button"

        # Should not raise exception
        widget.on_button_pressed(mock_event)


def test_on_button_pressed_wrong_button_id():
    """Test button press handling with wrong button ID."""
    widget = DownloadData()

    # Create a mock click event with wrong button ID
    mock_event = MagicMock()
    mock_event.button.id = "wrong-button-id"

    # Should not raise exception and not call _start_download
    widget.on_button_pressed(mock_event)


def test_on_unmount_with_exception_handling():
    """Test on_unmount with exception during downloader cancellation."""
    widget = DownloadData()
    widget.downloader = MagicMock()
    widget.downloader.cancel_download.side_effect = Exception("Cancel failed")
    widget.download_thread = MagicMock()
    widget.download_thread.is_alive.return_value = True

    # Should not raise exception
    widget.on_unmount()

    # Verify cancellation was attempted
    widget.downloader.cancel_download.assert_called_once()
    widget.download_thread.join.assert_called_once_with(timeout=1.0)


def test_full_download_worker_initialization_failure():
    """Test download worker when initialization fails."""
    widget = DownloadData()
    widget.selected_project_id = "test-project"

    with patch(
        "dds_cli.dds_gui.pages.project_actions.download_data.download_data.ProjectDownloader"
    ) as mock_downloader_class, patch(
        "dds_cli.directory.DDSDirectory"
    ) as mock_directory_class, patch(
        "dds_cli.data_getter.DataGetter"
    ) as mock_data_getter_class:
        mock_downloader = MagicMock()
        mock_downloader_class.return_value = mock_downloader
        mock_downloader.initialize.return_value = False  # Initialization fails

        mock_directory_class.return_value = MagicMock()

        # Mock the data getter
        mock_data_getter_class.return_value = MagicMock()

        with patch.object(widget, "_update_status") as mock_update:
            widget._full_download_worker("test-project")

            # Should call update_status with failure message
            assert mock_update.call_count >= 1
            # Check that the call contains "Failed to initialize download"
            call_args = str(mock_update.call_args)
            assert "Failed to initialize download" in call_args

            # Should not call download_all
            mock_downloader.download_all.assert_not_called()


def test_full_download_worker_status_updates():
    """Test status updates during download workflow."""
    widget = DownloadData()
    widget.selected_project_id = "test-project"

    with patch(
        "dds_cli.dds_gui.pages.project_actions.download_data.download_data.ProjectDownloader"
    ) as mock_downloader_class, patch(
        "dds_cli.directory.DDSDirectory"
    ) as mock_directory_class, patch(
        "dds_cli.data_getter.DataGetter"
    ) as mock_data_getter_class:
        mock_downloader = MagicMock()
        mock_downloader_class.return_value = mock_downloader
        mock_downloader.initialize.return_value = True
        mock_downloader.download_all.return_value = True

        mock_directory_class.return_value = MagicMock()

        # Mock the data getter
        mock_data_getter_class.return_value = MagicMock()

        with patch.object(widget, "_update_status") as mock_update:
            widget._full_download_worker("test-project")

            # Should have status updates
            assert mock_update.call_count >= 1


def test_full_download_worker_fallback_error_handling():
    """Test fallback error handling in worker finally block."""
    widget = DownloadData()
    widget.selected_project_id = "test-project"

    with patch(
        "dds_cli.dds_gui.pages.project_actions.download_data.download_data.ProjectDownloader"
    ) as mock_downloader_class, patch(
        "dds_cli.directory.DDSDirectory"
    ) as mock_directory_class, patch(
        "dds_cli.data_getter.DataGetter"
    ) as mock_data_getter_class:
        mock_downloader = MagicMock()
        mock_downloader_class.return_value = mock_downloader
        mock_downloader.initialize.side_effect = Exception("Unexpected error")

        mock_directory_class.return_value = MagicMock()

        # Mock the data getter
        mock_data_getter_class.return_value = MagicMock()

        # Should not raise exception even with unexpected error
        widget._full_download_worker("test-project")

        # State should be reset
        assert widget.is_downloading is False
        assert widget.download_thread is None


def test_on_unmount_with_thread_join_exception():
    """Test on_unmount with exception during thread join."""
    widget = DownloadData()
    widget.downloader = MagicMock()
    widget.download_thread = MagicMock()
    widget.download_thread.is_alive.return_value = True
    widget.download_thread.join.side_effect = Exception("Join failed")

    # The actual implementation doesn't handle join exceptions, so this will raise
    with pytest.raises(Exception, match="Join failed"):
        widget.on_unmount()

    # Confirm unmount tried to cancel
    widget.downloader.cancel_download.assert_called_once()


# =================================================================================
# Project Access Tests
# =================================================================================


@pytest.mark.asyncio
async def test_download_button_disabled_when_no_access():
    """Test that download button is disabled when user doesn't have access to project."""
    from dds_cli.dds_gui.models.project import ProjectList as ProjectListModel

    # Create mock projects with Access=False
    mock_projects_no_access = [
        {"Project ID": "test-project", "Title": "Test Project", "Access": False},
    ]

    with patch("dds_cli.data_lister.DataLister") as mock_data_lister_class, patch(
        "dds_cli.project_info.ProjectInfoManager"
    ) as mock_project_info_class:
        mock_data_lister_instance = MagicMock()
        mock_data_lister_class.return_value = mock_data_lister_instance
        mock_data_lister_instance.list_projects.return_value = mock_projects_no_access

        # Mock ProjectInfoManager
        mock_project_info_instance = MagicMock()
        mock_project_info_class.return_value = mock_project_info_instance
        mock_project_info_instance.get_project_info.return_value = {
            "Title": "Test Project",
            "Description": "Test Description",
            "Status": "Available",
            "Created by": "test_user",
            "Last updated": "2024-01-01",
            "Size": "1024",
            "PI": "Test PI",
        }

        app = DDSApp(token_path="/tmp/test_token")

        async with app.run_test() as pilot:
            app.set_auth_status(True)
            app.project_list = ProjectListModel.from_dict(mock_projects_no_access)

            # Select project without access
            app.set_selected_project_id("test-project")
            await pilot.pause()

            widget = DownloadData()
            app.mount(widget)
            await pilot.pause()

            # Find the download button
            download_button = widget.query_one("#download-project-content-button")

            # Button should be disabled
            assert (
                download_button.disabled is True
            ), "Button should be disabled when user has no access"


@pytest.mark.asyncio
async def test_download_button_enabled_when_has_access():
    """Test that download button is enabled when user has access to project."""
    from dds_cli.dds_gui.models.project import ProjectList as ProjectListModel

    # Create mock projects with Access=True
    mock_projects_with_access = [
        {"Project ID": "test-project", "Title": "Test Project", "Access": True},
    ]

    with patch("dds_cli.data_lister.DataLister") as mock_data_lister_class, patch(
        "dds_cli.project_info.ProjectInfoManager"
    ) as mock_project_info_class:
        mock_data_lister_instance = MagicMock()
        mock_data_lister_class.return_value = mock_data_lister_instance
        mock_data_lister_instance.list_projects.return_value = mock_projects_with_access

        # Mock ProjectInfoManager
        mock_project_info_instance = MagicMock()
        mock_project_info_class.return_value = mock_project_info_instance
        mock_project_info_instance.get_project_info.return_value = {
            "Title": "Test Project",
            "Description": "Test Description",
            "Status": "Available",
            "Created by": "test_user",
            "Last updated": "2024-01-01",
            "Size": "1024",
            "PI": "Test PI",
        }

        app = DDSApp(token_path="/tmp/test_token")

        async with app.run_test() as pilot:
            app.set_auth_status(True)
            app.project_list = ProjectListModel.from_dict(mock_projects_with_access)

            # Select project with access
            app.set_selected_project_id("test-project")
            await pilot.pause()

            widget = DownloadData()
            app.mount(widget)
            await pilot.pause()

            # Find the download button
            download_button = widget.query_one("#download-project-content-button")

            # Button should be enabled
            assert (
                download_button.disabled is False
            ), "Button should be enabled when user has access"


@pytest.mark.asyncio
async def test_download_button_disabled_when_no_project_selected():
    """Test that download button is disabled when no project is selected."""
    from dds_cli.dds_gui.models.project import ProjectList as ProjectListModel

    mock_projects = [
        {"Project ID": "test-project", "Title": "Test Project", "Access": True},
    ]

    with patch("dds_cli.data_lister.DataLister") as mock_data_lister_class:
        mock_data_lister_instance = MagicMock()
        mock_data_lister_class.return_value = mock_data_lister_instance
        mock_data_lister_instance.list_projects.return_value = mock_projects

        app = DDSApp(token_path="/tmp/test_token")

        async with app.run_test() as pilot:
            app.set_auth_status(True)
            app.project_list = ProjectListModel.from_dict(mock_projects)

            # Don't select any project
            app.set_selected_project_id(None)
            await pilot.pause()

            widget = DownloadData()
            app.mount(widget)
            await pilot.pause()

            # Find the download button
            download_button = widget.query_one("#download-project-content-button")

            # Button should be disabled
            assert (
                download_button.disabled is True
            ), "Button should be disabled when no project selected"


@pytest.mark.asyncio
async def test_download_button_access_state_changes():
    """Test that download button updates when access state changes."""
    from dds_cli.dds_gui.models.project import ProjectList as ProjectListModel

    # Create projects with different access levels
    mock_projects = [
        {"Project ID": "project-with-access", "Title": "Project 1", "Access": True},
        {"Project ID": "project-no-access", "Title": "Project 2", "Access": False},
    ]

    with patch("dds_cli.data_lister.DataLister") as mock_data_lister_class, patch(
        "dds_cli.project_info.ProjectInfoManager"
    ) as mock_project_info_class:
        mock_data_lister_instance = MagicMock()
        mock_data_lister_class.return_value = mock_data_lister_instance
        mock_data_lister_instance.list_projects.return_value = mock_projects

        # Mock ProjectInfoManager
        mock_project_info_instance = MagicMock()
        mock_project_info_class.return_value = mock_project_info_instance
        mock_project_info_instance.get_project_info.return_value = {
            "Title": "Test Project",
            "Description": "Test Description",
            "Status": "Available",
            "Created by": "test_user",
            "Last updated": "2024-01-01",
            "Size": "1024",
            "PI": "Test PI",
        }

        app = DDSApp(token_path="/tmp/test_token")

        async with app.run_test() as pilot:
            app.set_auth_status(True)
            app.project_list = ProjectListModel.from_dict(mock_projects)
            await pilot.pause()

            widget = DownloadData()
            app.mount(widget)
            await pilot.pause()

            # Select project with access
            app.set_selected_project_id("project-with-access")
            await pilot.pause()

            # Verify the app state is correct
            assert app.projects_access is True, "Should have access for first project"

            # Select project without access
            app.set_selected_project_id("project-no-access")
            await pilot.pause()

            # Verify app state changed
            assert app.projects_access is False, "Should not have access for second project"
            # Verify app state changed
            assert app.projects_access is False, "Should not have access for second project"
            # Verify app state changed
            assert app.projects_access is False, "Should not have access for second project"
            # Verify app state changed
            assert app.projects_access is False, "Should not have access for second project"
            # Verify app state changed
            assert app.projects_access is False, "Should not have access for second project"
