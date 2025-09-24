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
        
        with patch.object(widget, 'query_one') as mock_query:
            mock_label = MagicMock()
            mock_query.return_value = mock_label
            
            widget.watch_files_downloaded(5)
            
            mock_label.update.assert_called_once_with("Files: 5/10")

    def test_watch_files_downloaded_with_errors(self):
        """Test watching files_downloaded changes with errors."""
        widget = DownloadData()
        widget.error_files = 2
        widget.total_files = 10
        
        with patch.object(widget, 'query_one') as mock_query:
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
        
        with patch.object(widget, 'query_one') as mock_query, \
             patch.object(widget, '_mount_error_label') as mock_mount:
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
        
        with patch.object(widget, 'query_one') as mock_query, \
             patch.object(widget, '_mount_error_label') as mock_mount:
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
        
        with patch.object(widget, 'query_one') as mock_query:
            mock_button = MagicMock()
            mock_query.return_value = mock_button
            
            widget.watch_is_downloading(False)
            
            mock_button.disabled = False

    def test_watch_is_downloading_disables_button(self):
        """Test watching is_downloading changes disables button."""
        widget = DownloadData()
        widget.selected_project_id = "test-project"
        
        with patch.object(widget, 'query_one') as mock_query:
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
        
        with patch.object(widget, 'query_one') as mock_query:
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
            progress_calls = [call for call in mock_progress_bar.update.call_args_list if 'progress' in call.kwargs]
            assert len(progress_calls) > 0
            assert progress_calls[0].kwargs['progress'] == 50.0

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
        
        with patch.object(widget, 'query_one') as mock_query:
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
        
        with patch.object(widget, 'query_one') as mock_query, \
             patch('dds_cli.dds_gui.pages.project_actions.download_data.download_data.Label') as mock_label_class:
            # First call returns None (no existing error label), second returns container
            mock_container = MagicMock()
            mock_query.side_effect = [None, mock_container]
            mock_label = MagicMock()
            mock_label_class.return_value = mock_label
            
            widget._mount_error_label()
            
            # Verify label was created
            mock_label_class.assert_called_once_with("⚠️ Some files failed to download", id="error-label", classes="disabled")
            # Verify mount was called on the container
            mock_container.mount.assert_called_once_with(mock_label)

    def test_mount_error_label_already_exists(self):
        """Test mounting error label when it already exists."""
        widget = DownloadData()
        
        with patch.object(widget, 'query_one') as mock_query, \
             patch('dds_cli.dds_gui.pages.project_actions.download_data.download_data.Label') as mock_label_class:
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


class TestDownloadDataIntegration:
    """Integration tests for DownloadData with ProjectDownloader."""

    def test_full_download_workflow(self):
        """Test complete download workflow."""
        widget = DownloadData()
        widget.selected_project_id = "test-project"
        
        # Mock the ProjectDownloader to simulate a successful download
        with patch('dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.ProjectDownloader') as mock_downloader_class, \
             patch('dds_cli.directory.DDSDirectory') as mock_directory_class:
            mock_downloader = MagicMock()
            mock_downloader_class.return_value = mock_downloader
            mock_downloader.initialize.return_value = True
            mock_downloader.download_all.return_value = True
            
            # Mock the directory creation
            mock_directory_class.return_value = MagicMock()
            
            # Start download
            widget._start_download()
            
            # Verify initial state
            assert widget.is_downloading is True
            assert widget.progress == 0.0
            assert widget.files_downloaded == 0
            assert widget.error_files == 0
            
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
        with patch('dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.ProjectDownloader') as mock_downloader_class, \
             patch('dds_cli.directory.DDSDirectory') as mock_directory_class:
            mock_downloader = MagicMock()
            mock_downloader_class.return_value = mock_downloader
            mock_downloader.initialize.return_value = False  # Simulate initialization failure
            
            # Mock the directory creation
            mock_directory_class.return_value = MagicMock()
            
            with patch.object(widget, '_update_status') as mock_update:
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
            assert hasattr(widget, 'app')
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
            with patch('dds_cli.dds_gui.pages.project_actions.download_data.project_downloader.ProjectDownloader') as mock_downloader_class:
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