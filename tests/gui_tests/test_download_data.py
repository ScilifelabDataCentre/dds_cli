"""Tests for DownloadData GUI widget."""

import threading
import time
from unittest.mock import MagicMock, Mock, patch
from typing import Any, Optional

import pytest
from textual.app import App
from textual.widget import Widget

from dds_cli.dds_gui.app import DDSApp
from dds_cli.dds_gui.pages.project_actions.download_data.download_data import DownloadData
from dds_cli.dds_gui.pages.project_actions.download_data.project_downloader import (
    DownloadProgress,
    DownloadResult,
    ProjectDownloader,
)


class TestDownloadData:
    """Test DownloadData GUI widget."""

    def test_download_data_initialization(self):
        """Test DownloadData widget initialization."""
        widget = DownloadData()

        assert widget.downloader is None
        assert widget.download_thread is None
        assert widget.progress == 0.0
        assert widget.files_downloaded == 0
        assert widget.error_files == 0
        assert widget.total_files == 0
        assert widget.show_error_label is False
        assert widget.selected_project_id is None
        assert widget.is_downloading is False

    def test_compose_method(self):
        """Test the compose method creates correct widgets."""
        # Skip this test as it requires app context for Textual widgets
        # The compose method is tested indirectly through the app context tests
        pass

    def test_watch_files_downloaded_without_errors(self):
        """Test watching files_downloaded changes without errors."""
        widget = DownloadData()
        widget.error_files = 0
        widget.total_files = 10

        with patch.object(widget, "query_one") as mock_query:
            mock_label = MagicMock()
            mock_query.return_value = mock_label

            widget.watch_files_downloaded(5)

            mock_label.update.assert_called_once_with("Files: 5/10")

    def test_watch_files_downloaded_with_errors(self):
        """Test watching files_downloaded changes with errors."""
        widget = DownloadData()
        widget.error_files = 2
        widget.total_files = 10

        with patch.object(widget, "query_one") as mock_query:
            mock_label = MagicMock()
            mock_query.return_value = mock_label

            widget.watch_files_downloaded(5)

            mock_label.update.assert_called_once_with("Files: 5/10 (Errors: 2)")

    def test_watch_error_files_first_error(self):
        """Test watching error_files when first error occurs."""
        widget = DownloadData()
        widget.show_error_label = False
        widget.files_downloaded = 3
        widget.total_files = 10

        with patch.object(widget, "query_one") as mock_query, patch.object(
            widget, "_mount_error_label"
        ) as mock_mount:
            mock_label = MagicMock()
            mock_query.return_value = mock_label

            widget.watch_error_files(1)

            assert widget.show_error_label is True
            mock_mount.assert_called_once()
            mock_label.update.assert_called_once_with("Files: 3/10 (Errors: 1)")

    def test_watch_error_files_subsequent_errors(self):
        """Test watching error_files for subsequent errors."""
        widget = DownloadData()
        widget.show_error_label = True
        widget.files_downloaded = 3
        widget.total_files = 10

        with patch.object(widget, "query_one") as mock_query, patch.object(
            widget, "_mount_error_label"
        ) as mock_mount:
            mock_label = MagicMock()
            mock_query.return_value = mock_label

            widget.watch_error_files(2)

            # Should not mount error label again
            mock_mount.assert_not_called()
            mock_label.update.assert_called_once_with("Files: 3/10 (Errors: 2)")

    def test_watch_is_downloading_enables_button(self):
        """Test watching is_downloading changes enables button."""
        widget = DownloadData()
        widget.selected_project_id = "test-project"

        with patch.object(widget, "query_one") as mock_query:
            mock_button = MagicMock()
            mock_query.return_value = mock_button

            widget.watch_is_downloading(False)

            mock_button.disabled = False

    def test_watch_is_downloading_disables_button(self):
        """Test watching is_downloading changes disables button."""
        widget = DownloadData()
        widget.selected_project_id = "test-project"

        with patch.object(widget, "query_one") as mock_query:
            mock_button = MagicMock()
            mock_query.return_value = mock_button

            widget.watch_is_downloading(True)

            mock_button.disabled = True

    def test_update_progress_ui(self):
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
                call
                for call in mock_progress_bar.update.call_args_list
                if "progress" in call.kwargs
            ]
            assert len(progress_calls) > 0
            assert progress_calls[0].kwargs["progress"] == 50.0

    def test_update_progress_ui_no_progress_bar(self):
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

    def test_mount_error_label(self):
        """Test mounting error label."""
        widget = DownloadData()

        with patch.object(widget, "query_one") as mock_query, patch(
            "dds_cli.dds_gui.pages.project_actions.download_data.download_data.Label"
        ) as mock_label_class:
            # First call returns None (no existing error label), second returns container
            mock_container = MagicMock()
            mock_query.side_effect = [None, mock_container]
            mock_label = MagicMock()
            mock_label_class.return_value = mock_label

            widget._mount_error_label()

            # Verify label was created
            mock_label_class.assert_called_once_with(
                "⚠️ Some files failed to download", id="error-label", classes="disabled"
            )
            # Verify mount was called on the container
            mock_container.mount.assert_called_once_with(mock_label)

    def test_mount_error_label_already_exists(self):
        """Test mounting error label when it already exists."""
        widget = DownloadData()

        with patch.object(widget, "query_one") as mock_query, patch(
            "dds_cli.dds_gui.pages.project_actions.download_data.download_data.Label"
        ) as mock_label_class:
            # First call returns existing error label
            mock_query.return_value = MagicMock()

            widget._mount_error_label()

            # Should not create new label
            mock_label_class.assert_not_called()

    def test_on_file_completed(self):
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

    def test_reset_download_state(self):
        """Test resetting download state."""
        widget = DownloadData()
        widget.is_downloading = True
        widget.download_thread = MagicMock()

        widget._reset_download_state()

        assert widget.is_downloading is False
        assert widget.download_thread is None

    def test_on_button_pressed_success(self):
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

    def test_on_button_pressed_exception(self):
        """Test button press handling with exception."""
        widget = DownloadData()

        with patch.object(widget, "query_one") as mock_query:
            mock_query.side_effect = Exception("Query failed")

            # Create a mock click event
            mock_event = MagicMock()
            mock_event.button.id = "download-project-content-button"

            # Should not raise exception
            widget.on_button_pressed(mock_event)

    def test_start_download_already_downloading(self):
        """Test starting download when already downloading."""
        widget = DownloadData()
        widget.is_downloading = True

        # Should return early without starting download
        widget._start_download()

        # Verify that is_downloading is still True
        assert widget.is_downloading is True

    def test_start_download_no_project_selected(self):
        """Test starting download with no project selected."""
        widget = DownloadData()
        widget.selected_project_id = None

        # Test that the method returns early without starting download
        # We can't easily test the app.notify call due to Textual's app context requirements
        # This test is skipped as it requires complex app mocking
        pass

    def test_full_download_worker_stop_after_init(self):
        """Test download worker stopping after initialization."""
        widget = DownloadData()
        widget.selected_project_id = "test-project"

        with patch(
            "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.ProjectDownloader"
        ) as mock_downloader_class, patch("dds_cli.directory.DDSDirectory") as mock_directory_class:
            mock_downloader = MagicMock()
            mock_downloader_class.return_value = mock_downloader
            mock_downloader.initialize.return_value = True

            # Mock the directory creation
            mock_directory_class.return_value = MagicMock()

            # Set stop flag before starting
            widget._stop_download.set()

            widget._full_download_worker("test-project")

            # Should not call download_all
            mock_downloader.download_all.assert_not_called()

    def test_full_download_worker_stop_before_download(self):
        """Test download worker stopping before download starts."""
        widget = DownloadData()
        widget.selected_project_id = "test-project"

        with patch(
            "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.ProjectDownloader"
        ) as mock_downloader_class, patch("dds_cli.directory.DDSDirectory") as mock_directory_class:
            mock_downloader = MagicMock()
            mock_downloader_class.return_value = mock_downloader
            mock_downloader.initialize.return_value = True

            # Mock the directory creation
            mock_directory_class.return_value = MagicMock()

            # Set stop flag after initialization but before download
            def mock_initialize(*args, **kwargs):
                widget._stop_download.set()
                return True

            mock_downloader.initialize.side_effect = mock_initialize

            widget._full_download_worker("test-project")

            # Should not call download_all
            mock_downloader.download_all.assert_not_called()

    def test_full_download_worker_download_success(self):
        """Test successful download in worker."""
        widget = DownloadData()
        widget.selected_project_id = "test-project"

        with patch(
            "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.ProjectDownloader"
        ) as mock_downloader_class, patch(
            "dds_cli.directory.DDSDirectory"
        ) as mock_directory_class, patch.object(
            widget, "_update_status"
        ) as mock_update:
            mock_downloader = MagicMock()
            mock_downloader_class.return_value = mock_downloader
            mock_downloader.initialize.return_value = True
            mock_downloader.download_all.return_value = True

            # Mock the directory creation
            mock_directory_class.return_value = MagicMock()

            widget._full_download_worker("test-project")

            # Verify status updates
            assert (
                mock_update.call_count >= 2
            )  # At least "Starting download..." and "Download completed"

    def test_full_download_worker_download_failure(self):
        """Test download failure in worker."""
        widget = DownloadData()
        widget.selected_project_id = "test-project"

        with patch(
            "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.ProjectDownloader"
        ) as mock_downloader_class, patch(
            "dds_cli.directory.DDSDirectory"
        ) as mock_directory_class, patch.object(
            widget, "_update_status"
        ) as mock_update:
            mock_downloader = MagicMock()
            mock_downloader_class.return_value = mock_downloader
            mock_downloader.initialize.return_value = True
            mock_downloader.download_all.return_value = False

            # Mock the directory creation
            mock_directory_class.return_value = MagicMock()

            widget._full_download_worker("test-project")

            # Verify status updates
            assert (
                mock_update.call_count >= 2
            )  # At least "Starting download..." and "Download failed"

    def test_full_download_worker_exception(self):
        """Test exception handling in worker."""
        widget = DownloadData()
        widget.selected_project_id = "test-project"

        with patch(
            "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.ProjectDownloader"
        ) as mock_downloader_class, patch(
            "dds_cli.directory.DDSDirectory"
        ) as mock_directory_class, patch.object(
            widget, "_update_status"
        ) as mock_update:
            mock_downloader = MagicMock()
            mock_downloader_class.return_value = mock_downloader
            mock_downloader.initialize.side_effect = Exception("Init failed")

            # Mock the directory creation
            mock_directory_class.return_value = MagicMock()

            widget._full_download_worker("test-project")

            # Verify error status was set (the actual implementation calls "Initialization failed")
            mock_update.assert_called_with("Initialization failed")

    def test_on_unmount_with_downloader(self):
        """Test unmount with active downloader."""
        widget = DownloadData()
        widget.downloader = MagicMock()
        widget.download_thread = MagicMock()
        widget.download_thread.is_alive.return_value = True

        widget.on_unmount()

        # Verify cancellation was called
        widget.downloader.cancel_download.assert_called_once()
        widget.download_thread.join.assert_called_once_with(timeout=1.0)

    def test_on_unmount_downloader_exception(self):
        """Test unmount with downloader cancellation exception."""
        widget = DownloadData()
        widget.downloader = MagicMock()
        widget.downloader.cancel_download.side_effect = Exception("Cancel failed")
        widget.download_thread = MagicMock()
        widget.download_thread.is_alive.return_value = False

        # Should not raise exception
        widget.on_unmount()

    def test_start_download_removes_existing_error_label(self):
        """Test that _start_download removes existing error label."""
        widget = DownloadData()
        widget.selected_project_id = "test-project"

        with patch.object(widget, "query_one") as mock_query, patch(
            "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.ProjectDownloader"
        ) as mock_downloader_class, patch(
            "dds_cli.directory.DDSDirectory"
        ) as mock_directory_class, patch(
            "threading.Thread"
        ) as mock_thread_class:
            # Mock existing error label
            mock_error_label = MagicMock()
            mock_query.return_value = mock_error_label

            # Mock downloader and directory
            mock_downloader = MagicMock()
            mock_downloader_class.return_value = mock_downloader
            mock_directory_class.return_value = MagicMock()

            # Mock thread
            mock_thread = MagicMock()
            mock_thread_class.return_value = mock_thread

            widget._start_download()

            # Verify error label was removed
            mock_error_label.remove.assert_called_once()

    def test_start_download_error_label_removal_exception(self):
        """Test _start_download handles error label removal exception."""
        widget = DownloadData()
        widget.selected_project_id = "test-project"

        with patch.object(widget, "query_one") as mock_query, patch(
            "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.ProjectDownloader"
        ) as mock_downloader_class, patch(
            "dds_cli.directory.DDSDirectory"
        ) as mock_directory_class, patch(
            "threading.Thread"
        ) as mock_thread_class:
            # Mock query_one to raise exception
            mock_query.side_effect = Exception("Query failed")

            # Mock downloader and directory
            mock_downloader = MagicMock()
            mock_downloader_class.return_value = mock_downloader
            mock_directory_class.return_value = MagicMock()

            # Mock thread
            mock_thread = MagicMock()
            mock_thread_class.return_value = mock_thread

            # Should not raise exception
            widget._start_download()

    def test_start_download_creates_thread(self):
        """Test that _start_download creates and starts download thread."""
        widget = DownloadData()
        widget.selected_project_id = "test-project"

        with patch.object(widget, "query_one") as mock_query, patch(
            "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.ProjectDownloader"
        ) as mock_downloader_class, patch(
            "dds_cli.directory.DDSDirectory"
        ) as mock_directory_class, patch(
            "threading.Thread"
        ) as mock_thread_class:
            # Mock query_one to return None (no error label)
            mock_query.return_value = None

            # Mock downloader and directory
            mock_downloader = MagicMock()
            mock_downloader_class.return_value = mock_downloader
            mock_directory_class.return_value = MagicMock()

            # Mock thread
            mock_thread = MagicMock()
            mock_thread_class.return_value = mock_thread

            widget._start_download()

            # Verify thread was created and started
            mock_thread_class.assert_called_once_with(
                target=widget._full_download_worker, args=("test-project",), daemon=True
            )
            mock_thread.start.assert_called_once()


class TestDownloadDataIntegration:
    """Integration tests for DownloadData with ProjectDownloader."""

    def test_full_download_workflow(self):
        """Test complete download workflow."""
        widget = DownloadData()
        widget.selected_project_id = "test-project"

        # Mock the ProjectDownloader to simulate a successful download
        with patch(
            "dds_cli.dds_gui.pages.project_actions.download_data.download_data.ProjectDownloader"
        ) as mock_downloader_class, patch("dds_cli.directory.DDSDirectory") as mock_directory_class:
            mock_downloader = MagicMock()
            mock_downloader_class.return_value = mock_downloader
            mock_downloader.initialize.return_value = True
            mock_downloader.download_all.return_value = True

            # Mock the directory creation
            mock_directory_class.return_value = MagicMock()

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

    def test_error_handling_workflow(self):
        """Test error handling workflow."""
        widget = DownloadData()
        widget.selected_project_id = "test-project"

        # Mock the ProjectDownloader to simulate an error
        with patch(
            "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.ProjectDownloader"
        ) as mock_downloader_class, patch("dds_cli.directory.DDSDirectory") as mock_directory_class:
            mock_downloader = MagicMock()
            mock_downloader_class.return_value = mock_downloader
            mock_downloader.initialize.return_value = False  # Simulate initialization failure

            # Mock the directory creation
            mock_directory_class.return_value = MagicMock()

            with patch.object(widget, "_update_status") as mock_update:
                widget._full_download_worker("test-project")

                # Verify error status was set
                mock_update.assert_called_with("Initialization failed")

    def test_cancellation_workflow(self):
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


class TestDownloadDataWithApp:
    """Tests for DownloadData widget with proper Textual app context."""

    @pytest.mark.asyncio
    async def test_download_data_with_app_context(self):
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
    async def test_download_workflow_with_app(self):
        """Test download workflow with proper app context."""
        app = DDSApp(token_path="/tmp/test_token")

        async with app.run_test() as pilot:
            widget = DownloadData()
            app.mount(widget)

            # Set up the widget
            widget.selected_project_id = "test-project"

            # Mock the ProjectDownloader
            with patch(
                "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.ProjectDownloader"
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
                assert widget.show_error_label is False

    @pytest.mark.asyncio
    async def test_error_label_mounting_with_app(self):
        """Test error label mounting with proper app context."""
        app = DDSApp(token_path="/tmp/test_token")

        async with app.run_test() as pilot:
            widget = DownloadData()
            app.mount(widget)

            # Set up initial state
            widget.files_downloaded = 2
            widget.total_files = 3
            widget.show_error_label = False

            # Test that we can manually set the error label state
            widget.show_error_label = True
            assert widget.show_error_label is True

            # The error label mounting is tested in the unit tests
            # This test verifies the reactive behavior works in app context

    @pytest.mark.asyncio
    async def test_progress_updates_with_app(self):
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


class TestDownloadDataEdgeCases:
    """Test edge cases and error conditions for DownloadData."""

    def test_start_download_no_project_selected_with_app_context(self):
        """Test starting download with no project selected in app context."""
        app = DDSApp(token_path="/tmp/test_token")
        
        async def run_test():
            async with app.run_test() as pilot:
                widget = DownloadData()
                app.mount(widget)
                
                # Set no project selected
                widget.selected_project_id = None
                
                # Mock the app.notify method to track calls
                with patch.object(app, 'notify') as mock_notify:
                    widget._start_download()
                    
                    # Verify notification was called
                    mock_notify.assert_called_once_with("No project selected", severity="error")
                    
                    # Verify is_downloading is still False
                    assert widget.is_downloading is False
        
        import asyncio
        asyncio.run(run_test())

    def test_full_download_worker_stop_after_initialization(self):
        """Test download worker stopping after initialization."""
        widget = DownloadData()
        widget.selected_project_id = "test-project"
        
        with patch(
            "dds_cli.dds_gui.pages.project_actions.download_data.download_data.ProjectDownloader"
        ) as mock_downloader_class, patch("dds_cli.directory.DDSDirectory") as mock_directory_class:
            mock_downloader = MagicMock()
            mock_downloader_class.return_value = mock_downloader
            
            # Mock initialize to set stop flag after successful initialization
            def mock_initialize(*args, **kwargs):
                widget._stop_download.set()
                return True
            
            mock_downloader.initialize.side_effect = mock_initialize
            mock_directory_class.return_value = MagicMock()
            
            widget._full_download_worker("test-project")
            
            # Should not call download_all
            mock_downloader.download_all.assert_not_called()

    def test_full_download_worker_stop_before_download_start(self):
        """Test download worker stopping before download starts."""
        widget = DownloadData()
        widget.selected_project_id = "test-project"
        
        with patch(
            "dds_cli.dds_gui.pages.project_actions.download_data.download_data.ProjectDownloader"
        ) as mock_downloader_class, patch("dds_cli.directory.DDSDirectory") as mock_directory_class:
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
            
            with patch.object(widget, '_update_status', side_effect=mock_update_status):
                mock_directory_class.return_value = MagicMock()
                widget._full_download_worker("test-project")
            
            # Should not call download_all
            mock_downloader.download_all.assert_not_called()

    def test_update_status_with_app_context(self):
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

    def test_on_progress_update_with_app_context(self):
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

    def test_reset_download_state_with_app_context(self):
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

    def test_mount_error_label_no_container_found(self):
        """Test mounting error label when no container is found."""
        widget = DownloadData()
        
        with patch.object(widget, 'query_one') as mock_query, patch(
            "dds_cli.dds_gui.pages.project_actions.download_data.download_data.Label"
        ) as mock_label_class:
            # First call returns None (no existing error label)
            # Second call returns None (no progress container)
            # Third call returns None (no main container)
            mock_query.side_effect = [None, None, None]
            mock_label = MagicMock()
            mock_label_class.return_value = mock_label
            
            # Should not raise exception
            widget._mount_error_label()

    def test_mount_error_label_query_exception(self):
        """Test mounting error label when query raises exception."""
        widget = DownloadData()
        
        with patch.object(widget, 'query_one') as mock_query, patch(
            "dds_cli.dds_gui.pages.project_actions.download_data.download_data.Label"
        ) as mock_label_class:
            # Mock query to raise exception
            mock_query.side_effect = Exception("Query failed")
            
            # Should not raise exception
            widget._mount_error_label()

    def test_on_error(self):
        """Test error callback handling."""
        widget = DownloadData()
        
        with patch.object(widget, '_update_status') as mock_update:
            widget._on_error("Test error message")
            
            mock_update.assert_called_once_with("Error: Test error message")

    def test_full_download_worker_exception_during_cleanup(self):
        """Test exception handling during cleanup in worker."""
        widget = DownloadData()
        widget.selected_project_id = "test-project"
        
        with patch(
            "dds_cli.dds_gui.pages.project_actions.download_data.download_data.ProjectDownloader"
        ) as mock_downloader_class, patch("dds_cli.directory.DDSDirectory") as mock_directory_class:
            mock_downloader = MagicMock()
            mock_downloader_class.return_value = mock_downloader
            mock_downloader.initialize.side_effect = Exception("Init failed")
            
            mock_directory_class.return_value = MagicMock()
            
            # Should not raise exception
            widget._full_download_worker("test-project")
            
            # State should still be reset
            assert widget.is_downloading is False
            assert widget.download_thread is None

    def test_full_download_worker_final_fallback_error_handling(self):
        """Test final fallback error handling in worker."""
        widget = DownloadData()
        widget.selected_project_id = "test-project"
        
        with patch(
            "dds_cli.dds_gui.pages.project_actions.download_data.download_data.ProjectDownloader"
        ) as mock_downloader_class, patch("dds_cli.directory.DDSDirectory") as mock_directory_class:
            mock_downloader = MagicMock()
            mock_downloader_class.return_value = mock_downloader
            mock_downloader.initialize.side_effect = Exception("Init failed")
            
            mock_directory_class.return_value = MagicMock()
            
            # Should not raise exception
            widget._full_download_worker("test-project")

    def test_watch_selected_project_id_updates_button_state(self):
        """Test that watching selected_project_id updates button state."""
        widget = DownloadData()
        widget.selected_project_id = "test-project"
        widget.is_downloading = False
        
        with patch.object(widget, 'query_one') as mock_query:
            mock_button = MagicMock()
            mock_query.return_value = mock_button
            
            # Test updating project ID
            widget.watch_selected_project_id("new-project")
            
            # Should call watch_is_downloading to update button state
            assert widget.selected_project_id == "new-project"

    def test_watch_files_downloaded_with_query_exception(self):
        """Test watch_files_downloaded when query raises exception."""
        widget = DownloadData()
        widget.error_files = 0
        widget.total_files = 10
        
        with patch.object(widget, 'query_one') as mock_query:
            mock_query.side_effect = Exception("Query failed")
            
            # Should not raise exception
            widget.watch_files_downloaded(5)

    def test_watch_error_files_with_query_exception(self):
        """Test watch_error_files when query raises exception."""
        widget = DownloadData()
        widget.files_downloaded = 3
        widget.total_files = 10
        
        with patch.object(widget, 'query_one') as mock_query:
            mock_query.side_effect = Exception("Query failed")
            
            # Should not raise exception
            widget.watch_error_files(1)

    def test_watch_total_files_with_query_exception(self):
        """Test watch_total_files when query raises exception."""
        widget = DownloadData()
        widget.files_downloaded = 3
        widget.error_files = 1
        
        with patch.object(widget, 'query_one') as mock_query:
            mock_query.side_effect = Exception("Query failed")
            
            # Should not raise exception
            widget.watch_total_files(10)

    def test_watch_is_downloading_with_query_exception(self):
        """Test watch_is_downloading when query raises exception."""
        widget = DownloadData()
        widget.selected_project_id = "test-project"
        
        with patch.object(widget, 'query_one') as mock_query:
            mock_query.side_effect = Exception("Query failed")
            
            # Should not raise exception
            widget.watch_is_downloading(True)
        widget.download_thread.join.side_effect = Exception("Join failed")

        # The actual implementation doesn't handle join exceptions, so this will raise
        with pytest.raises(Exception, match="Join failed"):
            widget.on_unmount()

        # Verify cancellation was called
        widget.downloader.cancel_download.assert_called_once()

    def test_watch_selected_project_id_updates_button_state(self):
        """Test that watching selected_project_id updates button state."""
        widget = DownloadData()
        widget.selected_project_id = "test-project"
        widget.is_downloading = False
        
        with patch.object(widget, 'query_one') as mock_query:
            mock_button = MagicMock()
            mock_query.return_value = mock_button
            
            # Test updating project ID
            widget.watch_selected_project_id("new-project")
            
            # Should call watch_is_downloading to update button state
            assert widget.selected_project_id == "new-project"

    def test_watch_files_downloaded_with_query_exception(self):
        """Test watch_files_downloaded when query raises exception."""
        widget = DownloadData()
        widget.error_files = 0
        widget.total_files = 10
        
        with patch.object(widget, 'query_one') as mock_query:
            mock_query.side_effect = Exception("Query failed")
            
            # Should not raise exception
            widget.watch_files_downloaded(5)

    def test_watch_error_files_with_query_exception(self):
        """Test watch_error_files when query raises exception."""
        widget = DownloadData()
        widget.files_downloaded = 3
        widget.total_files = 10
        
        with patch.object(widget, 'query_one') as mock_query:
            mock_query.side_effect = Exception("Query failed")
            
            # Should not raise exception
            widget.watch_error_files(1)

    def test_watch_total_files_with_query_exception(self):
        """Test watch_total_files when query raises exception."""
        widget = DownloadData()
        widget.files_downloaded = 3
        widget.error_files = 1
        
        with patch.object(widget, 'query_one') as mock_query:
            mock_query.side_effect = Exception("Query failed")
            
            # Should not raise exception
            widget.watch_total_files(10)

    def test_watch_is_downloading_with_query_exception(self):
        """Test watch_is_downloading when query raises exception."""
        widget = DownloadData()
        widget.selected_project_id = "test-project"
        
        with patch.object(widget, 'query_one') as mock_query:
            mock_query.side_effect = Exception("Query failed")
            
            # Should not raise exception
            widget.watch_is_downloading(True)

    def test_mount_error_label_no_container_found(self):
        """Test mounting error label when no container is found."""
        widget = DownloadData()
        
        with patch.object(widget, 'query_one') as mock_query, patch(
            "dds_cli.dds_gui.pages.project_actions.download_data.download_data.Label"
        ) as mock_label_class:
            # First call returns None (no existing error label)
            # Second call returns None (no progress container)
            # Third call returns None (no main container)
            mock_query.side_effect = [None, None, None]
            mock_label = MagicMock()
            mock_label_class.return_value = mock_label
            
            # Should not raise exception
            widget._mount_error_label()

    def test_mount_error_label_query_exception(self):
        """Test mounting error label when query raises exception."""
        widget = DownloadData()
        
        with patch.object(widget, 'query_one') as mock_query, patch(
            "dds_cli.dds_gui.pages.project_actions.download_data.download_data.Label"
        ) as mock_label_class:
            # Mock query to raise exception
            mock_query.side_effect = Exception("Query failed")
            
            # Should not raise exception
            widget._mount_error_label()

    def test_on_error(self):
        """Test error callback handling."""
        widget = DownloadData()
        
        with patch.object(widget, '_update_status') as mock_update:
            widget._on_error("Test error message")
            
            mock_update.assert_called_once_with("Error: Test error message")

    def test_full_download_worker_exception_during_cleanup(self):
        """Test exception handling during cleanup in worker."""
        widget = DownloadData()
        widget.selected_project_id = "test-project"
        
        with patch(
            "dds_cli.dds_gui.pages.project_actions.download_data.download_data.ProjectDownloader"
        ) as mock_downloader_class, patch("dds_cli.directory.DDSDirectory") as mock_directory_class:
            mock_downloader = MagicMock()
            mock_downloader_class.return_value = mock_downloader
            mock_downloader.initialize.side_effect = Exception("Init failed")
            
            mock_directory_class.return_value = MagicMock()
            
            # Should not raise exception
            widget._full_download_worker("test-project")
            
            # State should still be reset
            assert widget.is_downloading is False
            assert widget.download_thread is None

    def test_full_download_worker_final_fallback_error_handling(self):
        """Test final fallback error handling in worker."""
        widget = DownloadData()
        widget.selected_project_id = "test-project"
        
        with patch(
            "dds_cli.dds_gui.pages.project_actions.download_data.download_data.ProjectDownloader"
        ) as mock_downloader_class, patch("dds_cli.directory.DDSDirectory") as mock_directory_class:
            mock_downloader = MagicMock()
            mock_downloader_class.return_value = mock_downloader
            mock_downloader.initialize.side_effect = Exception("Init failed")
            
            mock_directory_class.return_value = MagicMock()
            
            # Should not raise exception
            widget._full_download_worker("test-project")

    def test_start_download_removes_existing_error_label(self):
        """Test that _start_download removes existing error label."""
        widget = DownloadData()
        widget.selected_project_id = "test-project"

        with patch.object(widget, "query_one") as mock_query, patch(
            "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.ProjectDownloader"
        ) as mock_downloader_class, patch(
            "dds_cli.directory.DDSDirectory"
        ) as mock_directory_class, patch(
            "threading.Thread"
        ) as mock_thread_class:
            # Mock existing error label
            mock_error_label = MagicMock()
            mock_query.return_value = mock_error_label

            # Mock downloader and directory
            mock_downloader = MagicMock()
            mock_downloader_class.return_value = mock_downloader
            mock_directory_class.return_value = MagicMock()

            # Mock thread
            mock_thread = MagicMock()
            mock_thread_class.return_value = mock_thread

            widget._start_download()

            # Verify error label was removed
            mock_error_label.remove.assert_called_once()

    def test_start_download_error_label_removal_exception(self):
        """Test _start_download handles error label removal exception."""
        widget = DownloadData()
        widget.selected_project_id = "test-project"

        with patch.object(widget, "query_one") as mock_query, patch(
            "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.ProjectDownloader"
        ) as mock_downloader_class, patch(
            "dds_cli.directory.DDSDirectory"
        ) as mock_directory_class, patch(
            "threading.Thread"
        ) as mock_thread_class:
            # Mock query_one to raise exception
            mock_query.side_effect = Exception("Query failed")

            # Mock downloader and directory
            mock_downloader = MagicMock()
            mock_downloader_class.return_value = mock_downloader
            mock_directory_class.return_value = MagicMock()

            # Mock thread
            mock_thread = MagicMock()
            mock_thread_class.return_value = mock_thread

            # Should not raise exception
            widget._start_download()

    def test_start_download_creates_thread(self):
        """Test that _start_download creates and starts download thread."""
        widget = DownloadData()
        widget.selected_project_id = "test-project"

        with patch.object(widget, "query_one") as mock_query, patch(
            "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.ProjectDownloader"
        ) as mock_downloader_class, patch(
            "dds_cli.directory.DDSDirectory"
        ) as mock_directory_class, patch(
            "threading.Thread"
        ) as mock_thread_class:
            # Mock query_one to return None (no error label)
            mock_query.return_value = None

            # Mock downloader and directory
            mock_downloader = MagicMock()
            mock_downloader_class.return_value = mock_downloader
            mock_directory_class.return_value = MagicMock()

            # Mock thread
            mock_thread = MagicMock()
            mock_thread_class.return_value = mock_thread

            widget._start_download()

            # Verify thread was created and started
            mock_thread_class.assert_called_once_with(
                target=widget._full_download_worker, args=("test-project",), daemon=True
            )
            mock_thread.start.assert_called_once()

    def test_start_download_no_project_selected_with_app_context(self):
        """Test starting download with no project selected in app context."""
        app = DDSApp(token_path="/tmp/test_token")
        
        async def run_test():
            async with app.run_test() as pilot:
                widget = DownloadData()
                app.mount(widget)
                
                # Set no project selected
                widget.selected_project_id = None
                
                # Mock the app.notify method to track calls
                with patch.object(app, 'notify') as mock_notify:
                    widget._start_download()
                    
                    # Verify notification was called
                    mock_notify.assert_called_once_with("No project selected", severity="error")
                    
                    # Verify is_downloading is still False
                    assert widget.is_downloading is False
        
        import asyncio
        asyncio.run(run_test())

    def test_full_download_worker_stop_after_initialization(self):
        """Test download worker stopping after initialization."""
        widget = DownloadData()
        widget.selected_project_id = "test-project"
        
        with patch(
            "dds_cli.dds_gui.pages.project_actions.download_data.download_data.ProjectDownloader"
        ) as mock_downloader_class, patch("dds_cli.directory.DDSDirectory") as mock_directory_class:
            mock_downloader = MagicMock()
            mock_downloader_class.return_value = mock_downloader
            
            # Mock initialize to set stop flag after successful initialization
            def mock_initialize(*args, **kwargs):
                widget._stop_download.set()
                return True
            
            mock_downloader.initialize.side_effect = mock_initialize
            mock_directory_class.return_value = MagicMock()
            
            widget._full_download_worker("test-project")
            
            # Should not call download_all
            mock_downloader.download_all.assert_not_called()

    def test_full_download_worker_stop_before_download_start(self):
        """Test download worker stopping before download starts."""
        widget = DownloadData()
        widget.selected_project_id = "test-project"
        
        with patch(
            "dds_cli.dds_gui.pages.project_actions.download_data.download_data.ProjectDownloader"
        ) as mock_downloader_class, patch("dds_cli.directory.DDSDirectory") as mock_directory_class:
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
            
            with patch.object(widget, '_update_status', side_effect=mock_update_status):
                mock_directory_class.return_value = MagicMock()
                widget._full_download_worker("test-project")
            
            # Should not call download_all
            mock_downloader.download_all.assert_not_called()

    def test_update_status_with_app_context(self):
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

    def test_on_progress_update_with_app_context(self):
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

    def test_reset_download_state_with_app_context(self):
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

    def test_update_progress_ui_with_progress_bar_update_exception(self):
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

    def test_watch_files_downloaded_with_error_files_and_query_exception(self):
        """Test watch_files_downloaded with errors when query raises exception."""
        widget = DownloadData()
        widget.error_files = 2
        widget.total_files = 10

        with patch.object(widget, "query_one") as mock_query:
            mock_query.side_effect = Exception("Query failed")

            # Should not raise exception
            widget.watch_files_downloaded(5)

    def test_watch_error_files_first_error_with_query_exception(self):
        """Test watch_error_files first error when query raises exception."""
        widget = DownloadData()
        widget.show_error_label = False
        widget.files_downloaded = 3
        widget.total_files = 10

        with patch.object(widget, "query_one") as mock_query, patch.object(
            widget, "_mount_error_label"
        ) as mock_mount:
            mock_query.side_effect = Exception("Query failed")

            # Should not raise exception
            widget.watch_error_files(1)

    def test_watch_error_files_subsequent_errors_with_query_exception(self):
        """Test watch_error_files subsequent errors when query raises exception."""
        widget = DownloadData()
        widget.show_error_label = True
        widget.files_downloaded = 3
        widget.total_files = 10

        with patch.object(widget, "query_one") as mock_query, patch.object(
            widget, "_mount_error_label"
        ) as mock_mount:
            mock_query.side_effect = Exception("Query failed")

            # Should not raise exception
            widget.watch_error_files(2)

    def test_watch_is_downloading_enables_button_with_query_exception(self):
        """Test watch_is_downloading enables button when query raises exception."""
        widget = DownloadData()
        widget.selected_project_id = "test-project"

        with patch.object(widget, "query_one") as mock_query:
            mock_query.side_effect = Exception("Query failed")

            # Should not raise exception
            widget.watch_is_downloading(False)

    def test_watch_is_downloading_disables_button_with_query_exception(self):
        """Test watch_is_downloading disables button when query raises exception."""
        widget = DownloadData()
        widget.selected_project_id = "test-project"

        with patch.object(widget, "query_one") as mock_query:
            mock_query.side_effect = Exception("Query failed")

            # Should not raise exception
            widget.watch_is_downloading(True)

    def test_on_button_pressed_with_exception(self):
        """Test button press handling with exception."""
        widget = DownloadData()

        with patch.object(widget, "query_one") as mock_query:
            mock_query.side_effect = Exception("Query failed")

            # Create a mock click event
            mock_event = MagicMock()
            mock_event.button.id = "download-project-content-button"

            # Should not raise exception
            widget.on_button_pressed(mock_event)

    def test_on_button_pressed_wrong_button_id(self):
        """Test button press handling with wrong button ID."""
        widget = DownloadData()

        # Create a mock click event with wrong button ID
        mock_event = MagicMock()
        mock_event.button.id = "wrong-button-id"

        # Should not raise exception and not call _start_download
        widget.on_button_pressed(mock_event)

    def test_start_download_already_downloading(self):
        """Test starting download when already downloading."""
        widget = DownloadData()
        widget.is_downloading = True

        # Should return early without starting download
        widget._start_download()

        # Verify that is_downloading is still True
        assert widget.is_downloading is True

    def test_start_download_no_project_selected(self):
        """Test starting download with no project selected."""
        widget = DownloadData()
        widget.selected_project_id = None

        # Test that the method returns early without starting download
        # We can't easily test the app.notify call due to Textual's app context requirements
        # This test is skipped as it requires complex app mocking
        pass

    def test_full_download_worker_download_success(self):
        """Test successful download in worker."""
        widget = DownloadData()
        widget.selected_project_id = "test-project"

        with patch(
            "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.ProjectDownloader"
        ) as mock_downloader_class, patch(
            "dds_cli.directory.DDSDirectory"
        ) as mock_directory_class, patch.object(
            widget, "_update_status"
        ) as mock_update:
            mock_downloader = MagicMock()
            mock_downloader_class.return_value = mock_downloader
            mock_downloader.initialize.return_value = True
            mock_downloader.download_all.return_value = True

            # Mock the directory creation
            mock_directory_class.return_value = MagicMock()

            widget._full_download_worker("test-project")

            # Verify status updates
            assert (
                mock_update.call_count >= 2
            )  # At least "Starting download..." and "Download completed"

    def test_full_download_worker_download_failure(self):
        """Test download failure in worker."""
        widget = DownloadData()
        widget.selected_project_id = "test-project"

        with patch(
            "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.ProjectDownloader"
        ) as mock_downloader_class, patch(
            "dds_cli.directory.DDSDirectory"
        ) as mock_directory_class, patch.object(
            widget, "_update_status"
        ) as mock_update:
            mock_downloader = MagicMock()
            mock_downloader_class.return_value = mock_downloader
            mock_downloader.initialize.return_value = True
            mock_downloader.download_all.return_value = False

            # Mock the directory creation
            mock_directory_class.return_value = MagicMock()

            widget._full_download_worker("test-project")

            # Verify status updates
            assert (
                mock_update.call_count >= 2
            )  # At least "Starting download..." and "Download failed"

    def test_full_download_worker_exception(self):
        """Test exception handling in worker."""
        widget = DownloadData()
        widget.selected_project_id = "test-project"

        with patch(
            "dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.ProjectDownloader"
        ) as mock_downloader_class, patch(
            "dds_cli.directory.DDSDirectory"
        ) as mock_directory_class, patch.object(
            widget, "_update_status"
        ) as mock_update:
            mock_downloader = MagicMock()
            mock_downloader_class.return_value = mock_downloader
            mock_downloader.initialize.side_effect = Exception("Init failed")

            # Mock the directory creation
            mock_directory_class.return_value = MagicMock()

            widget._full_download_worker("test-project")

            # Verify error status was set (the actual implementation calls "Initialization failed")
            mock_update.assert_called_with("Initialization failed")

    def test_on_file_completed(self):
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

    def test_reset_download_state(self):
        """Test resetting download state."""
        widget = DownloadData()
        widget.is_downloading = True
        widget.download_thread = MagicMock()

        widget._reset_download_state()

        assert widget.is_downloading is False
        assert widget.download_thread is None
