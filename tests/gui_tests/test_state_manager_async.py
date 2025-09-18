"""Tests for DDS State Manager async functionality."""

import pathlib
from unittest.mock import patch, MagicMock
import pytest

from dds_cli.dds_gui.dds_state_manager import DDSStateManager
import dds_cli.exceptions

TOKEN_PATH = pathlib.Path("custom") / "token" / "path"

# Test data
MOCK_PROJECTS = [
    {"Project ID": "project-001", "Title": "Project Alpha"},
    {"Project ID": "project-002", "Title": "Project Beta"},
]


# =================================================================================
# State Manager Async Functionality Tests
# =================================================================================


@pytest.mark.asyncio
async def test_sync_fetch_projects():
    """Test synchronous project fetching for initialization."""

    with patch("dds_cli.data_lister.DataLister") as mock_data_lister_class:
        # Mock DataLister to return projects
        mock_data_lister_instance = MagicMock()
        mock_data_lister_class.return_value = mock_data_lister_instance
        mock_data_lister_instance.list_projects.return_value = MOCK_PROJECTS

        app = DDSStateManager()

        async with app.run_test() as pilot:
            # Call sync fetch_projects
            app.fetch_projects()
            await pilot.pause()

            # Should have projects loaded
            assert app.project_list == MOCK_PROJECTS, "Projects should be loaded synchronously"
            assert app.projects_loading is False, "Loading state should be False after sync fetch"


@pytest.mark.asyncio
async def test_sync_fetch_projects_error():
    """Test synchronous project fetching error handling."""

    with patch("dds_cli.data_lister.DataLister") as mock_data_lister_class:
        # Mock DataLister to raise an error
        mock_data_lister_instance = MagicMock()
        mock_data_lister_class.return_value = mock_data_lister_instance
        mock_data_lister_instance.list_projects.side_effect = dds_cli.exceptions.ApiRequestError(
            "Connection failed"
        )

        app = DDSStateManager()
        notifications = []

        def capture_notify(message, **kwargs):
            notifications.append({"message": message, "severity": kwargs.get("severity")})

        app.notify = capture_notify

        async with app.run_test() as pilot:
            # Call sync fetch_projects
            app.fetch_projects()
            await pilot.pause()

            # Should handle error gracefully
            assert app.project_list is None, "Project list should be None after error"
            assert app.projects_loading is False, "Loading state should be False after error"
            assert len(notifications) > 0, "Should show error notification"
            assert "Failed to fetch projects" in notifications[-1]["message"]


@pytest.mark.asyncio
async def test_async_fetch_projects():
    """Test asynchronous project fetching."""

    with patch("dds_cli.data_lister.DataLister") as mock_data_lister_class:
        # Mock DataLister to return projects
        mock_data_lister_instance = MagicMock()
        mock_data_lister_class.return_value = mock_data_lister_instance
        mock_data_lister_instance.list_projects.return_value = MOCK_PROJECTS

        app = DDSStateManager()

        async with app.run_test() as pilot:
            # Call async fetch_projects_async
            app.fetch_projects_async()
            await pilot.pause()

            # Should have projects loaded
            assert app.project_list == MOCK_PROJECTS, "Projects should be loaded asynchronously"
            assert app.projects_loading is False, "Loading state should be False after async fetch"


@pytest.mark.asyncio
async def test_async_fetch_projects_error():
    """Test asynchronous project fetching error handling."""

    with patch("dds_cli.data_lister.DataLister") as mock_data_lister_class:
        # Mock DataLister to raise an error
        mock_data_lister_instance = MagicMock()
        mock_data_lister_class.return_value = mock_data_lister_instance
        mock_data_lister_instance.list_projects.side_effect = dds_cli.exceptions.ApiRequestError(
            "Connection failed"
        )

        app = DDSStateManager()
        notifications = []

        def capture_notify(message, **kwargs):
            notifications.append({"message": message, "severity": kwargs.get("severity")})

        app.notify = capture_notify

        async with app.run_test() as pilot:
            # Call async fetch_projects_async
            app.fetch_projects_async()
            await pilot.pause()

            # Should handle error gracefully
            assert app.project_list is None, "Project list should be None after error"
            assert app.projects_loading is False, "Loading state should be False after error"
            assert len(notifications) > 0, "Should show error notification"
            assert "Failed to fetch projects" in notifications[-1]["message"]


@pytest.mark.asyncio
async def test_watch_auth_status_sets_loading():
    """Test that auth status watcher sets loading state."""

    with patch("dds_cli.data_lister.DataLister") as mock_data_lister_class:
        # Mock DataLister to prevent authentication attempts
        mock_data_lister_instance = MagicMock()
        mock_data_lister_class.return_value = mock_data_lister_instance
        mock_data_lister_instance.list_projects.return_value = MOCK_PROJECTS

        app = DDSStateManager()

        async with app.run_test() as pilot:
            # Set auth status to True
            app.set_auth_status(True)
            await pilot.pause()

            # Should set loading state
            assert app.projects_loading is True, "Loading state should be set when authenticated"

            # Should not have projects yet (since we're not mounted)
            assert app.project_list is None, "Project list should be None when not mounted"


@pytest.mark.asyncio
async def test_watch_auth_status_clears_loading_on_logout():
    """Test that auth status watcher clears loading state on logout."""

    with patch("dds_cli.data_lister.DataLister") as mock_data_lister_class:
        # Mock DataLister to prevent authentication attempts
        mock_data_lister_instance = MagicMock()
        mock_data_lister_class.return_value = mock_data_lister_instance
        mock_data_lister_instance.list_projects.return_value = MOCK_PROJECTS

        app = DDSStateManager()

        async with app.run_test() as pilot:
            # Set auth status to True
            app.set_auth_status(True)
            await pilot.pause()

            # Should set loading state
            assert app.projects_loading is True, "Loading state should be set when authenticated"

            # Set auth status to False
            app.set_auth_status(False)
            await pilot.pause()

            # Should clear loading state and project list
            assert app.projects_loading is False, "Loading state should be cleared when logged out"
            assert app.project_list is None, "Project list should be cleared when logged out"
            assert (
                app.selected_project_id is None
            ), "Selected project should be cleared when logged out"


@pytest.mark.asyncio
async def test_mounted_flag_prevents_initial_fetch():
    """Test that mounted flag prevents initial project fetch."""

    with patch("dds_cli.data_lister.DataLister") as mock_data_lister_class:
        # Mock DataLister to prevent authentication attempts
        mock_data_lister_instance = MagicMock()
        mock_data_lister_class.return_value = mock_data_lister_instance
        mock_data_lister_instance.list_projects.return_value = MOCK_PROJECTS

        app = DDSStateManager()

        async with app.run_test() as pilot:
            # Set auth status to True (should not fetch projects since not mounted)
            app.set_auth_status(True)
            await pilot.pause()

            # Should set loading state but not fetch projects
            assert app.projects_loading is True, "Loading state should be set"
            assert app.project_list is None, "Project list should be None when not mounted"

            # Simulate mounting and manually trigger project fetch
            app._mounted = True
            app.fetch_projects_async()  # Manually trigger fetch
            await pilot.pause()

            # Should now fetch projects
            assert app.project_list == MOCK_PROJECTS, "Projects should be fetched when mounted"


@pytest.mark.asyncio
async def test_loading_state_callback_methods():
    """Test loading state callback methods."""

    app = DDSStateManager()

    async with app.run_test() as pilot:
        # Test _set_projects_loading
        app._set_projects_loading(True)
        assert app.projects_loading is True, "Should set loading state to True"

        app._set_projects_loading(False)
        assert app.projects_loading is False, "Should set loading state to False"

        # Test _on_projects_loaded
        app._on_projects_loaded(MOCK_PROJECTS)
        assert app.project_list == MOCK_PROJECTS, "Should set project list"
        assert app.projects_loading is False, "Should clear loading state"

        # Test _on_projects_error
        notifications = []

        def capture_notify(message, **kwargs):
            notifications.append({"message": message, "severity": kwargs.get("severity")})

        app.notify = capture_notify

        app._on_projects_error("Test error")
        assert app.project_list is None, "Should clear project list on error"
        assert app.projects_loading is False, "Should clear loading state on error"
        assert len(notifications) > 0, "Should show error notification"
        assert "Failed to fetch projects" in notifications[-1]["message"]


@pytest.mark.asyncio
async def test_dual_fetch_methods_coexistence():
    """Test that both sync and async fetch methods work correctly."""

    with patch("dds_cli.data_lister.DataLister") as mock_data_lister_class:
        # Mock DataLister to return projects
        mock_data_lister_instance = MagicMock()
        mock_data_lister_class.return_value = mock_data_lister_instance
        mock_data_lister_instance.list_projects.return_value = MOCK_PROJECTS

        app = DDSStateManager()

        async with app.run_test() as pilot:
            # Test sync method
            app.fetch_projects()
            await pilot.pause()
            assert app.project_list == MOCK_PROJECTS, "Sync method should work"

            # Clear and test async method
            app.project_list = None
            app.fetch_projects_async()
            await pilot.pause()
            assert app.project_list == MOCK_PROJECTS, "Async method should work"

            # Both methods should produce the same result
            assert app.projects_loading is False, "Loading state should be False after both methods"


@pytest.mark.asyncio
async def test_error_types_handling():
    """Test handling of different error types in async fetch."""

    error_types = [
        (dds_cli.exceptions.ApiRequestError("Request failed"), "error"),
        (dds_cli.exceptions.ApiResponseError("Response failed"), "error"),
        (dds_cli.exceptions.DDSCLIException("CLI failed"), "error"),
    ]

    for error, expected_severity in error_types:
        with patch("dds_cli.data_lister.DataLister") as mock_data_lister_class:
            # Mock DataLister to raise specific error
            mock_data_lister_instance = MagicMock()
            mock_data_lister_class.return_value = mock_data_lister_instance
            mock_data_lister_instance.list_projects.side_effect = error

            app = DDSStateManager()
            notifications = []

            def capture_notify(message, **kwargs):
                notifications.append({"message": message, "severity": kwargs.get("severity")})

            app.notify = capture_notify

            async with app.run_test() as pilot:
                # Call async fetch_projects_async
                app.fetch_projects_async()
                await pilot.pause()

                # Should handle error gracefully
                assert (
                    app.project_list is None
                ), f"Project list should be None after {type(error).__name__}"
                assert (
                    app.projects_loading is False
                ), f"Loading state should be False after {type(error).__name__}"
                assert (
                    len(notifications) > 0
                ), f"Should show error notification for {type(error).__name__}"
                assert (
                    notifications[-1]["severity"] == expected_severity
                ), f"Should show {expected_severity} severity for {type(error).__name__}"
