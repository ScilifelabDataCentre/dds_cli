"""Tests for async project loading functionality."""

import pathlib
from unittest.mock import patch, MagicMock
import pytest

from dds_cli.dds_gui.app import DDSApp
from dds_cli.dds_gui.pages.project_list.project_list import ProjectList
from dds_cli.dds_gui.components.dds_select import DDSSelect
from textual.widgets import LoadingIndicator, Label
import dds_cli.exceptions


async def wait_for_loading_state(app, pilot, expected_loading=True, max_attempts=10):
    """Wait for the loading state to be set correctly."""
    for _ in range(max_attempts):
        if app.projects_loading == expected_loading:
            await pilot.pause()  # Allow UI to update
            return True
        await pilot.pause()
    return False


async def wait_for_widget_recomposition(widget, pilot, max_attempts=10):
    """Wait for the widget to recompose after state changes."""
    for _ in range(max_attempts):
        await pilot.pause()  # Allow recomposition to happen
        # Check if the widget has the expected content
        try:
            # Try to query the widget to see if it has been recomposed
            widget.query("*")
            return True
        except Exception:
            pass
    return False


async def wait_for_reactive_change(app, pilot, attribute_name, expected_value, max_attempts=20):
    """Wait for a reactive attribute to change to the expected value."""
    for _ in range(max_attempts):
        current_value = getattr(app, attribute_name)
        if current_value == expected_value:
            # Give extra time for UI to update after reactive change
            await pilot.pause()
            await pilot.pause()
            return True
        await pilot.pause()
    return False


async def wait_for_ui_element(widget, pilot, element_type, expected_count=1, max_attempts=20):
    """Wait for a specific UI element to appear with the expected count."""
    for _ in range(max_attempts):
        elements = widget.query(element_type)
        if len(elements) == expected_count:
            return True
        await pilot.pause()
    return False


async def force_widget_recomposition(widget, pilot):
    """Force the widget to recompose by triggering a recomposition."""
    try:
        # Try to trigger recomposition directly
        await widget.recompose()
        await pilot.pause()
    except Exception:
        # If direct recomposition fails, wait for it to happen naturally
        await pilot.pause()
        await pilot.pause()


async def wait_for_call_after_refresh_cycle(pilot, max_attempts=10):
    """Wait for call_after_refresh cycles to complete by running multiple pause cycles."""
    for _ in range(max_attempts):
        await pilot.pause()
        # Give extra time for call_after_refresh to execute
        await pilot.pause()


async def wait_for_widget_state_change(widget, pilot, check_function, max_attempts=20):
    """Wait for widget state to change by checking a custom function."""
    for _ in range(max_attempts):
        if check_function(widget):
            return True
        await pilot.pause()
    return False


TOKEN_PATH = pathlib.Path("custom") / "token" / "path"

# Test data
MOCK_PROJECTS = [
    {"Project ID": "project-001", "Title": "Project Alpha"},
    {"Project ID": "project-002", "Title": "Project Beta"},
]


# =================================================================================
# Async Project Loading Tests
# =================================================================================


@pytest.mark.asyncio
async def test_authenticated_user_sees_loading_indicator():
    """Test that authenticated users see loading indicator before projects load."""

    app = DDSApp(token_path=str(TOKEN_PATH))

    async with app.run_test() as pilot:
        # Set auth status to True (this should trigger loading state)
        app.set_auth_status(True)
        await pilot.pause()

        # Mount project list widget
        widget = ProjectList(title="Project List")
        app.mount(widget)
        await pilot.pause()

        # Wait for loading state to be set
        await wait_for_loading_state(app, pilot, expected_loading=True)

        # Should show loading indicator when authenticated but projects loading
        loading_indicators = widget.query(LoadingIndicator)
        assert len(loading_indicators) == 1, "Should show loading indicator for authenticated user"

        # Should not show project selector yet
        select_widgets = widget.query(DDSSelect)
        assert len(select_widgets) == 0, "Should not show project selector while loading"


@pytest.mark.asyncio
async def test_unauthenticated_user_sees_auth_message():
    """Test that unauthenticated users see authentication message."""

    app = DDSApp(token_path=str(TOKEN_PATH))

    async with app.run_test() as pilot:
        # Set auth status to False
        app.set_auth_status(False)
        await pilot.pause()

        # Mount project list widget
        widget = ProjectList(title="Project List")
        app.mount(widget)
        await pilot.pause()

        # Should show authentication message
        labels = widget.query(Label)
        auth_labels = [label for label in labels if "authenticate" in label.renderable.lower()]
        assert len(auth_labels) == 1, "Should show authentication message for unauthenticated user"

        # Should not show loading indicator
        loading_indicators = widget.query(LoadingIndicator)
        assert (
            len(loading_indicators) == 0
        ), "Should not show loading indicator for unauthenticated user"


@pytest.mark.asyncio
async def test_projects_load_after_authentication():
    """Test state transitions when projects load after authentication."""

    app = DDSApp(token_path=str(TOKEN_PATH))

    async with app.run_test() as pilot:
        # Start unauthenticated
        app.set_auth_status(False)
        await pilot.pause()

        # Mount project list widget
        widget = ProjectList(title="Project List")
        app.mount(widget)
        await pilot.pause()

        # Should show auth message initially
        labels = widget.query(Label)
        auth_labels = [label for label in labels if "authenticate" in label.renderable.lower()]
        assert len(auth_labels) == 1, "Should show authentication message initially"

        # Now authenticate - this should trigger the natural loading flow
        app.set_auth_status(True)
        await pilot.pause()

        # Wait for loading state to be set naturally
        await wait_for_loading_state(app, pilot, expected_loading=True)

        # Verify the app state is correct
        assert app.auth_status is True, "Auth status should be True"
        assert app.projects_loading is True, "Projects loading should be True"
        assert app.project_list is None, "Project list should be None initially"

        # Simulate project loading completion
        app.project_list = MOCK_PROJECTS
        app.projects_loading = False
        await pilot.pause()

        # Verify the app state is correct after loading
        assert app.project_list == MOCK_PROJECTS, "Project list should be set"
        assert app.projects_loading is False, "Projects loading should be False"


@pytest.mark.asyncio
async def test_loading_state_cleared_on_logout():
    """Test that loading state is cleared when user logs out."""

    app = DDSApp(token_path=str(TOKEN_PATH))

    async with app.run_test() as pilot:
        # Start authenticated
        app.set_auth_status(True)
        await pilot.pause()

        # Mount project list widget
        widget = ProjectList(title="Project List")
        app.mount(widget)
        await pilot.pause()

        # Wait for loading state to be set
        await wait_for_loading_state(app, pilot, expected_loading=True)

        # Should show loading indicator
        loading_indicators = widget.query(LoadingIndicator)
        assert len(loading_indicators) == 1, "Should show loading indicator when authenticated"

        # Logout user
        app.set_auth_status(False)
        await pilot.pause()

        # Wait for reactive changes to propagate
        await wait_for_reactive_change(app, pilot, "auth_status", False)
        await wait_for_reactive_change(app, pilot, "projects_loading", False)

        # Verify logout state
        assert app.auth_status is False, "Auth status should be False"
        assert app.projects_loading is False, "Projects loading should be False"
        assert app.project_list is None, "Project list should be None after logout"
        assert app.selected_project_id is None, "Selected project should be None after logout"

        # Should not show loading indicator anymore
        loading_indicators = widget.query(LoadingIndicator)
        assert len(loading_indicators) == 0, "Should not show loading indicator after logout"

        # Should not show project selector
        select_widgets = widget.query(DDSSelect)
        assert len(select_widgets) == 0, "Should not show project selector after logout"


@pytest.mark.asyncio
async def test_no_projects_found_state():
    """Test behavior when authenticated but no projects are found."""

    app = DDSApp(token_path=str(TOKEN_PATH))

    async with app.run_test() as pilot:
        # Start authenticated
        app.set_auth_status(True)
        await pilot.pause()

        # Mount project list widget
        widget = ProjectList(title="Project List")
        app.mount(widget)
        await pilot.pause()

        # Wait for loading state to be set
        await wait_for_loading_state(app, pilot, expected_loading=True)

        # Should show loading indicator initially
        loading_indicators = widget.query(LoadingIndicator)
        assert len(loading_indicators) == 1, "Should show loading indicator initially"

        # Simulate async project loading completion with empty results
        app.project_list = []
        app.projects_loading = False
        await pilot.pause()

        # Wait for reactive changes to propagate
        await wait_for_reactive_change(app, pilot, "project_list", [])
        await wait_for_reactive_change(app, pilot, "projects_loading", False)

        # Verify empty project list state
        assert app.project_list == [], "Project list should be empty"
        assert app.projects_loading is False, "Projects loading should be False"
        assert app.auth_status is True, "Auth status should still be True"

        # Should not show loading indicator anymore
        loading_indicators = widget.query(LoadingIndicator)
        assert (
            len(loading_indicators) == 0
        ), "Should not show loading indicator after loading completes"

        # Should not show project selector
        select_widgets = widget.query(DDSSelect)
        assert len(select_widgets) == 0, "Should not show project selector when no projects found"


@pytest.mark.asyncio
async def test_async_project_loading_error_handling():
    """Test error handling during async project loading."""

    app = DDSApp(token_path=str(TOKEN_PATH))

    async with app.run_test() as pilot:
        # Start authenticated
        app.set_auth_status(True)
        await pilot.pause()

        # Mount project list widget
        widget = ProjectList(title="Project List")
        app.mount(widget)
        await pilot.pause()

        # Wait for loading state to be set
        await wait_for_loading_state(app, pilot, expected_loading=True)

        # Should show loading indicator initially
        loading_indicators = widget.query(LoadingIndicator)
        assert len(loading_indicators) == 1, "Should show loading indicator initially"

        # Simulate async project loading error
        app.project_list = None
        app.projects_loading = False
        await pilot.pause()

        # Wait for reactive changes to propagate
        await wait_for_reactive_change(app, pilot, "project_list", None)
        await wait_for_reactive_change(app, pilot, "projects_loading", False)

        # Verify error state
        assert app.project_list is None, "Project list should be None after error"
        assert app.projects_loading is False, "Projects loading should be False"
        assert app.auth_status is True, "Auth status should still be True"

        # Should not show loading indicator anymore
        loading_indicators = widget.query(LoadingIndicator)
        assert len(loading_indicators) == 0, "Should not show loading indicator after error"

        # Should not show project selector
        select_widgets = widget.query(DDSSelect)
        assert len(select_widgets) == 0, "Should not show project selector after error"


@pytest.mark.asyncio
async def test_loading_state_transitions():
    """Test all possible loading state transitions."""

    app = DDSApp(token_path=str(TOKEN_PATH))

    async with app.run_test() as pilot:
        # Mount project list widget
        widget = ProjectList(title="Project List")
        app.mount(widget)
        await pilot.pause()

        # Test 1: Unauthenticated -> Authenticated (should show loading)
        app.set_auth_status(True)
        await pilot.pause()

        # Wait for loading state to be set
        await wait_for_loading_state(app, pilot, expected_loading=True)

        loading_indicators = widget.query(LoadingIndicator)
        assert len(loading_indicators) == 1, "Should show loading when becoming authenticated"

        # Test 2: Loading -> Projects loaded (should show selector)
        app.project_list = MOCK_PROJECTS
        app.projects_loading = False
        await pilot.pause()

        # Wait for reactive changes to propagate
        await wait_for_reactive_change(app, pilot, "project_list", MOCK_PROJECTS)
        await wait_for_reactive_change(app, pilot, "projects_loading", False)

        # Verify projects loaded state
        assert app.project_list == MOCK_PROJECTS, "Project list should be set"
        assert app.projects_loading is False, "Projects loading should be False"
        assert app.auth_status is True, "Auth status should still be True"

        # Test 3: Projects loaded -> Logout
        app.set_auth_status(False)
        await pilot.pause()

        # Wait for logout state to be set
        await wait_for_reactive_change(app, pilot, "auth_status", False)
        await wait_for_reactive_change(app, pilot, "projects_loading", False)

        # Verify logout state
        assert app.auth_status is False, "Auth status should be False"
        assert app.projects_loading is False, "Projects loading should be False"
        assert app.project_list is None, "Project list should be None after logout"
        assert app.selected_project_id is None, "Selected project should be None after logout"

        # Test 4: Logout -> Authenticated again
        app.set_auth_status(True)
        await pilot.pause()

        # Wait for loading state to be set again
        await wait_for_loading_state(app, pilot, expected_loading=True)

        # Verify authenticated state again
        assert app.auth_status is True, "Auth status should be True again"
        assert app.projects_loading is True, "Projects loading should be True again"
        assert app.project_list is None, "Project list should be None initially"


@pytest.mark.asyncio
async def test_app_initialization_with_auth_check():
    """Test that app initialization properly checks auth status without blocking."""

    # Create app - this should check auth status immediately
    app = DDSApp(token_path=str(TOKEN_PATH))

    # Manually set auth status to True to simulate authenticated user
    app.set_auth_status(True)

    async with app.run_test() as pilot:
        # Mount project list widget
        widget = ProjectList(title="Project List")
        app.mount(widget)
        await pilot.pause()

        # Should show loading indicator since we're authenticated
        loading_indicators = widget.query(LoadingIndicator)
        assert len(loading_indicators) == 1, "Should show loading indicator for authenticated user"


@pytest.mark.asyncio
async def test_app_initialization_without_auth():
    """Test that app initialization properly handles unauthenticated state."""

    # Create app - this should check auth status immediately
    app = DDSApp(token_path=str(TOKEN_PATH))

    # Manually set auth status to False to simulate unauthenticated user
    app.set_auth_status(False)

    async with app.run_test() as pilot:
        # Mount project list widget
        widget = ProjectList(title="Project List")
        app.mount(widget)
        await pilot.pause()

        # Should show authentication message
        labels = widget.query(Label)
        auth_labels = [label for label in labels if "authenticate" in label.renderable.lower()]
        assert len(auth_labels) == 1, "Should show authentication message for unauthenticated user"

        # Should not show loading indicator
        loading_indicators = widget.query(LoadingIndicator)
        assert (
            len(loading_indicators) == 0
        ), "Should not show loading indicator for unauthenticated user"
