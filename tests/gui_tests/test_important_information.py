"""Comprehensive tests for the Important Information widget."""

from unittest.mock import MagicMock, patch

import pytest
from textual.widgets import Static

from dds_cli.dds_gui.app import DDSApp
from dds_cli.dds_gui.pages.important_information.important_information import ImportantInformation
from dds_cli.dds_gui.pages.important_information.components.motd_card import MOTDCard
from dds_cli.exceptions import ApiRequestError, ApiResponseError, DDSCLIException, NoMOTDsError


# =================================================================================
# Test Data
# =================================================================================

MOCK_MOTDS = [
    {
        "Created": "2025-01-08 09:15",
        "Message": "Important: Password policy update required.",
        "ID": 3,
    },
    {
        "Created": "2025-01-09 14:30",
        "Message": "New feature: Enhanced file upload capabilities.",
        "ID": 2,
    },
    {
        "Created": "2025-01-10 10:00",
        "Message": "System maintenance scheduled for tonight.",
        "ID": 1,
    },
]

EMPTY_MOTDS = []


# =================================================================================
# Unit Tests - Widget Initialization and Basic Functionality
# =================================================================================


@pytest.mark.asyncio
async def test_important_information_initialization():
    """Test that ImportantInformation widget initializes correctly."""

    app = DDSApp(token_path="test_path")

    async with app.run_test() as pilot:
        widget = ImportantInformation("Test MOTDs")
        app.mount(widget)
        await pilot.pause()

        # Test initial state - widget should be initialized but timer is set on mount
        assert widget.border_title == "TEST MOTDS"
        # After mount, timer should be set up and MOTDs might be fetched
        assert widget.motd_timer is not None


# =================================================================================
# UI Component Tests - MOTDCard and Container Rendering
# =================================================================================


@pytest.mark.asyncio
async def test_motd_cards_rendering_and_ordering():
    """Test MOTDCard rendering, content, and latest-first ordering."""

    app = DDSApp(token_path="test_path")

    async with app.run_test() as pilot:
        with patch(
            "dds_cli.motd_manager.MotdManager.list_all_active_motds", return_value=MOCK_MOTDS
        ):
            widget = ImportantInformation("Test MOTDs")
            app.mount(widget)
            await pilot.pause()

            # Check that MOTDCards are rendered
            motd_cards = widget.query(MOTDCard)
            assert len(motd_cards) == 3

            # Check that cards are in reverse order (latest first)
            cards_list = list(motd_cards)
            assert "2025-01-10 10:00" in cards_list[0].title  # Latest first
            assert "2025-01-09 14:30" in cards_list[1].title  # Middle
            assert "2025-01-08 09:15" in cards_list[2].title  # Oldest last

            # Test individual card content
            first_card = cards_list[0]
            assert first_card.title == "2025-01-10 10:00"
            assert "System maintenance scheduled" in first_card.message

            # Check that container exists
            container = widget.query_one("#motd-container")
            assert container is not None


@pytest.mark.asyncio
async def test_empty_state_handling():
    """Test empty state rendering for both None and empty list scenarios."""

    with patch("dds_cli.motd_manager.MotdManager.list_all_active_motds") as mock_list_motds:
        # Configure the mock to return empty list
        mock_list_motds.return_value = []

        app = DDSApp(token_path="test_path")

        async with app.run_test() as pilot:
            # Test with empty list from API - this prevents the widget from fetching real data
            widget = ImportantInformation("Test MOTDs")
            app.mount(widget)
            await pilot.pause()

            # Should show empty state
            assert widget.motds == []
            assert len(widget.query(MOTDCard)) == 0

            # Verify the MOTD manager was called correctly
            mock_list_motds.assert_called_with(table=False)

            # Empty state static widget should be present
            statics = widget.query(Static)
            empty_statics = [
                static for static in statics if "No important information" in static.renderable
            ]
            assert len(empty_statics) == 1

            # Test with None motds (manually set after creation)
            widget.remove()
            await pilot.pause()

            widget = ImportantInformation("Test MOTDs")
            widget.motds = None  # Set after creation but before mount
            app.mount(widget)
            await pilot.pause()

            # Check that no MOTDCards are rendered
            motd_cards = widget.query(MOTDCard)
            assert len(motd_cards) == 0

            # Check that empty state static widget is shown
            statics = widget.query(Static)
            empty_statics = [
                static for static in statics if "No important information" in static.renderable
            ]
            assert len(empty_statics) == 1


# =================================================================================
# Integration Tests - MOTD Fetching and Data Flow
# =================================================================================


@pytest.mark.asyncio
async def test_motd_fetching_integration():
    """Test MOTD fetching integration - success case and API calls."""

    app = DDSApp(token_path="test_path")

    async with app.run_test() as pilot:
        # Test successful fetching
        with patch(
            "dds_cli.motd_manager.MotdManager.list_all_active_motds", return_value=MOCK_MOTDS
        ) as mock_fetch:
            widget = ImportantInformation("Test MOTDs")
            app.mount(widget)
            await pilot.pause()

            # Verify that MotdManager was called
            mock_fetch.assert_called_once_with(table=False)

            # Verify that MOTDs were set
            assert widget.motds == MOCK_MOTDS

            # Verify that MOTDCards are rendered
            motd_cards = widget.query(MOTDCard)
            assert len(motd_cards) == 3


# =================================================================================
# Reactive Behavior Tests
# =================================================================================


@pytest.mark.asyncio
async def test_reactive_motd_updates():
    """Test that UI updates when MOTDs are changed reactively."""

    app = DDSApp(token_path="test_path")

    async with app.run_test() as pilot:
        with patch(
            "dds_cli.motd_manager.MotdManager.list_all_active_motds", return_value=EMPTY_MOTDS
        ):
            widget = ImportantInformation("Test MOTDs")
            app.mount(widget)
            await pilot.pause()

            # Initially no MOTDCards
            assert len(widget.query(MOTDCard)) == 0

            # Update MOTDs reactively
            widget.motds = MOCK_MOTDS
            await pilot.pause()

            # Now MOTDCards should be rendered
            motd_cards = widget.query(MOTDCard)
            assert len(motd_cards) == 3


# =================================================================================
# Update Methods Tests
# =================================================================================


@pytest.mark.asyncio
async def test_update_motds_method():
    """Test the update_motds method functionality and success notifications."""

    with patch("dds_cli.motd_manager.MotdManager.list_all_active_motds") as mock_list_motds:
        # Configure the mock to return empty list initially
        mock_list_motds.return_value = []

        app = DDSApp(token_path="test_path")

        # Create a MagicMock for the app's notify method to track calls
        mock_notify = MagicMock(side_effect=app.notify)
        app.notify = mock_notify

        async with app.run_test() as pilot:
            widget = ImportantInformation("Test MOTDs")
            app.mount(widget)
            await pilot.pause()

            # Clear mock call history from mount
            mock_notify.reset_mock()

            # Initially empty MOTDs from our mock
            assert widget.motds == []

            # Update using the method
            widget.update_motds(MOCK_MOTDS)
            await pilot.pause()

            # MOTDs should be updated
            assert widget.motds == MOCK_MOTDS

            # UI should reflect the change
            motd_cards = widget.query(MOTDCard)
            assert len(motd_cards) == 3

            # Verify notification was sent using MagicMock assertions
            mock_notify.assert_called()

            # Check the last call to notify
            last_call = mock_notify.call_args
            message = last_call[0][0]  # First positional argument
            severity = last_call[1]["severity"]  # Keyword argument

            assert "New important information available" in message
            assert severity == "information"


# =================================================================================
# Timer Tests
# =================================================================================


@pytest.mark.asyncio
async def test_timer_setup():
    """Test that timer is set up correctly with proper interval."""

    app = DDSApp(token_path="test_path")

    async with app.run_test() as pilot:
        with patch(
            "dds_cli.motd_manager.MotdManager.list_all_active_motds", return_value=MOCK_MOTDS
        ):
            widget = ImportantInformation("Test MOTDs")

            # Mock the set_interval method to capture calls
            with patch.object(widget, "set_interval", return_value=MagicMock()) as mock_timer:
                app.mount(widget)
                await pilot.pause()

                # Verify timer was set with correct interval (3600 seconds = 1 hour)
                mock_timer.assert_called_once_with(3600, widget.fetch_motds)


# =================================================================================
# Error Handling Tests
# =================================================================================


@pytest.mark.asyncio
async def test_fetch_motds_error_handling():
    """Test comprehensive error handling in fetch_motds method and notification display."""

    with patch("dds_cli.motd_manager.MotdManager.list_all_active_motds") as mock_list_motds:
        # Start with empty list for initial mount
        mock_list_motds.return_value = []

        app = DDSApp(token_path="test_path")

        # Track notifications by patching the app's notify method
        notifications_received = []
        original_notify = app.notify

        def capture_notify(message, *, severity="information", timeout=3.0, title=""):
            notifications_received.append(
                {"message": message, "severity": severity, "timeout": timeout, "title": title}
            )
            return original_notify(message, severity=severity, timeout=timeout, title=title)

        app.notify = capture_notify

        async with app.run_test() as pilot:
            # Start with mocked empty data to prevent real API calls
            widget = ImportantInformation("Test MOTDs")
            app.mount(widget)
            await pilot.pause()

            # Clear any notifications from mount
            notifications_received.clear()

            # Store initial state (should be empty from mock)
            initial_motds = widget.motds

            # Test ApiRequestError
            mock_list_motds.side_effect = ApiRequestError(message="Connection failed")
            widget.fetch_motds()
            # Widget should handle error gracefully - MOTDs should remain unchanged
            assert widget.motds == initial_motds
            # Verify error notification was sent
            assert len(notifications_received) > 0
            latest_notification = notifications_received[-1]
            assert "Connection failed" in latest_notification["message"]
            assert latest_notification["severity"] == "error"

            notifications_received.clear()

            # Test ApiResponseError
            mock_list_motds.side_effect = ApiResponseError(message="Invalid response")
            widget.fetch_motds()
            assert widget.motds == initial_motds
            # Verify error notification was sent
            assert len(notifications_received) > 0
            latest_notification = notifications_received[-1]
            assert "Invalid response" in latest_notification["message"]
            assert latest_notification["severity"] == "error"

            notifications_received.clear()

            # Test DDSCLIException
            mock_list_motds.side_effect = DDSCLIException(message="CLI error")
            widget.fetch_motds()
            assert widget.motds == initial_motds
            # Verify error notification was sent
            assert len(notifications_received) > 0
            latest_notification = notifications_received[-1]
            assert "CLI error" in latest_notification["message"]
            assert latest_notification["severity"] == "error"

            notifications_received.clear()

            # Test NoMOTDsError - should be handled silently without notification
            mock_list_motds.side_effect = NoMOTDsError(message="No MOTDs found")
            widget.fetch_motds()
            assert widget.motds is None
            # Verify no notification was sent for NoMOTDsError (handled silently)
            assert len(notifications_received) == 0

            # Verify that all our error scenarios called the mock appropriately
            assert mock_list_motds.call_count >= 4


# =================================================================================
# Integration Test - Full Workflow
# =================================================================================


@pytest.mark.asyncio
async def test_full_important_information_workflow():
    """Test complete workflow from mount to MOTD display."""

    app = DDSApp(token_path="test_path")

    async with app.run_test() as pilot:
        with patch(
            "dds_cli.motd_manager.MotdManager.list_all_active_motds", return_value=MOCK_MOTDS
        ) as mock_fetch:
            widget = ImportantInformation("Important Information")
            app.mount(widget)
            await pilot.pause()

            # 1. Widget should be initialized
            assert widget.border_title == "IMPORTANT INFORMATION"

            # 2. Timer should be set up
            assert widget.motd_timer is not None

            # 3. MOTDs should be fetched on mount
            mock_fetch.assert_called_with(table=False)
            assert widget.motds == MOCK_MOTDS

            # 4. UI should render MOTDCards in correct order
            motd_cards = list(widget.query(MOTDCard))
            assert len(motd_cards) == 3
            assert motd_cards[0].title == "2025-01-10 10:00"  # Latest first

            # 5. Container should be present
            container = widget.query_one("#motd-container")
            assert container is not None

            # 6. Test manual update
            new_motds = [{"Created": "2025-01-11 12:00", "Message": "New update"}]
            widget.update_motds(new_motds)
            await pilot.pause()

            assert widget.motds == new_motds
            updated_cards = widget.query(MOTDCard)
            assert len(updated_cards) == 1


# =================================================================================
# Performance and Edge Case Tests
# =================================================================================


@pytest.mark.asyncio
async def test_large_number_of_motds():
    """Test widget performance with many MOTDs."""

    # Create a large number of test MOTDs
    large_motds = []
    for i in range(100):
        large_motds.append(
            {"Created": f"2025-01-{i:02d} 10:00", "Message": f"MOTD number {i}", "ID": i}
        )

    app = DDSApp(token_path="test_path")

    async with app.run_test() as pilot:
        with patch(
            "dds_cli.motd_manager.MotdManager.list_all_active_motds", return_value=large_motds
        ):
            widget = ImportantInformation("Test MOTDs")
            app.mount(widget)
            await pilot.pause()

            # All MOTDs should be rendered
            assert widget.motds == large_motds
            assert len(widget.query(MOTDCard)) == 100
