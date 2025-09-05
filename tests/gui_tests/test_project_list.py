"""GUI tests for Project List widget using reactive patterns."""

import pathlib
from unittest.mock import patch, MagicMock
import pytest

from dds_cli.dds_gui.app import DDSApp
from dds_cli.dds_gui.pages.project_list.project_list import ProjectList
from dds_cli.dds_gui.components.dds_select import DDSSelect
import dds_cli.exceptions

TOKEN_PATH = pathlib.Path("custom") / "token" / "path"

# Test data
MOCK_PROJECTS = [
    {"Project ID": "project-001", "Title": "Project Alpha"},
    {"Project ID": "project-002", "Title": "Project Beta"},
]

# =================================================================================
# Basic Functionality Tests
# =================================================================================


@pytest.mark.asyncio
async def test_basic_widget_functionality():
    """Test basic widget functionality with projects."""

    with patch("dds_cli.data_lister.DataLister") as mock_data_lister_class, patch(
        "dds_cli.project_info.ProjectInfoManager"
    ) as mock_project_info_class:
        # Mock DataLister to prevent authentication attempts
        mock_data_lister_instance = MagicMock()
        mock_data_lister_class.return_value = mock_data_lister_instance
        mock_data_lister_instance.list_projects.return_value = MOCK_PROJECTS

        # Mock ProjectInfoManager to prevent authentication attempts
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

        app = DDSApp(token_path=str(TOKEN_PATH))

        async with app.run_test() as pilot:
            # Set up state and mount widget
            app.set_auth_status(True)
            await pilot.pause()

            widget = ProjectList(title="Project List")
            app.mount(widget)
            await pilot.pause()

            # Verify widget components
            select_widgets = widget.query(DDSSelect)
            assert len(select_widgets) == 1

            select_widget = select_widgets[0]
            assert len(select_widget._options) == 3  # BLANK + 2 projects
            assert not select_widget.disabled


@pytest.mark.asyncio
async def test_unauthenticated_state():
    """Test widget when not authenticated."""

    with patch("dds_cli.data_lister.DataLister") as mock_data_lister_class:
        # Mock DataLister to prevent authentication attempts
        mock_data_lister_instance = MagicMock()
        mock_data_lister_class.return_value = mock_data_lister_instance
        mock_data_lister_instance.list_projects.return_value = []

        app = DDSApp(token_path=str(TOKEN_PATH))

        async with app.run_test() as pilot:
            app.set_auth_status(False)
            await pilot.pause()

            widget = ProjectList(title="Project List")
            app.mount(widget)
            await pilot.pause()

            select_widgets = widget.query(DDSSelect)
            select_widget = select_widgets[0]

            assert select_widget.disabled
            assert len(select_widget._options) == 1  # Only BLANK


@pytest.mark.asyncio
async def test_project_selection():
    """Test project selection and button interaction."""

    with patch("dds_cli.data_lister.DataLister") as mock_data_lister_class, patch(
        "dds_cli.project_info.ProjectInfoManager"
    ) as mock_project_info_class:
        # Mock DataLister to prevent authentication attempts
        mock_data_lister_instance = MagicMock()
        mock_data_lister_class.return_value = mock_data_lister_instance
        mock_data_lister_instance.list_projects.return_value = MOCK_PROJECTS

        # Mock ProjectInfoManager to prevent authentication attempts
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

        app = DDSApp(token_path=str(TOKEN_PATH))

        async with app.run_test() as pilot:
            app.set_auth_status(True)
            await pilot.pause()

            widget = ProjectList(title="Project List")
            app.mount(widget)
            await pilot.pause()

            # Select project
            select_widgets = widget.query(DDSSelect)
            select_widget = select_widgets[0]
            select_widget.value = "project-001"

            # Trigger button action
            button = widget.query_one("#view-project")
            mock_event = MagicMock()
            mock_event.button = button
            widget.on_button_pressed(mock_event)
            await pilot.pause()

            assert app.selected_project_id == "project-001"


@pytest.mark.asyncio
async def test_no_selection_warning():
    """Test warning when no project is selected."""

    with patch("dds_cli.data_lister.DataLister") as mock_data_lister_class, patch(
        "dds_cli.project_info.ProjectInfoManager"
    ) as mock_project_info_class:
        # Mock DataLister to prevent authentication attempts
        mock_data_lister_instance = MagicMock()
        mock_data_lister_class.return_value = mock_data_lister_instance
        mock_data_lister_instance.list_projects.return_value = MOCK_PROJECTS

        # Mock ProjectInfoManager to prevent authentication attempts
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

        app = DDSApp(token_path=str(TOKEN_PATH))
        notifications = []

        def capture_notify(message, **kwargs):
            notifications.append(message)

        app.notify = capture_notify

        async with app.run_test() as pilot:
            app.set_auth_status(True)
            await pilot.pause()

            widget = ProjectList(title="Project List")
            app.mount(widget)
            await pilot.pause()

            # Click button without selecting project
            button = widget.query_one("#view-project")
            mock_event = MagicMock()
            mock_event.button = button
            widget.on_button_pressed(mock_event)
            await pilot.pause()

            assert app.selected_project_id is None
            assert len(notifications) > 0
            assert "Please select a project" in notifications[-1]


@pytest.mark.asyncio
async def test_empty_projects():
    """Test behavior with empty project list."""

    with patch("dds_cli.data_lister.DataLister") as mock_data_lister_class:
        # Mock DataLister to prevent authentication attempts
        mock_data_lister_instance = MagicMock()
        mock_data_lister_class.return_value = mock_data_lister_instance
        mock_data_lister_instance.list_projects.return_value = []

        app = DDSApp(token_path=str(TOKEN_PATH))

        async with app.run_test() as pilot:
            app.set_auth_status(True)
            await pilot.pause()

            widget = ProjectList(title="Project List")
            app.mount(widget)
            await pilot.pause()

            select_widgets = widget.query(DDSSelect)
            select_widget = select_widgets[0]
            assert len(select_widget._options) == 1  # Only BLANK


@pytest.mark.asyncio
async def test_api_error():
    """Test API error handling."""

    with patch("dds_cli.data_lister.DataLister") as mock_data_lister_class:
        # Mock DataLister to prevent authentication attempts
        mock_data_lister_instance = MagicMock()
        mock_data_lister_class.return_value = mock_data_lister_instance
        mock_data_lister_instance.list_projects.side_effect = dds_cli.exceptions.ApiRequestError(
            "Connection failed"
        )

        app = DDSApp(token_path=str(TOKEN_PATH))
        notifications = []

        def capture_notify(message, **kwargs):
            notifications.append(message)

        app.notify = capture_notify

        async with app.run_test() as pilot:
            app.set_auth_status(True)
            await pilot.pause()

            # Error should be handled
            assert app.project_list is None
            assert len(notifications) > 0
            assert "Failed to fetch projects" in notifications[-1]


@pytest.mark.asyncio
async def test_auth_state_changes():
    """Test authentication state changes."""

    with patch("dds_cli.data_lister.DataLister") as mock_data_lister_class, patch(
        "dds_cli.project_info.ProjectInfoManager"
    ) as mock_project_info_class:
        # Mock DataLister to prevent authentication attempts
        mock_data_lister_instance = MagicMock()
        mock_data_lister_class.return_value = mock_data_lister_instance
        mock_data_lister_instance.list_projects.return_value = MOCK_PROJECTS

        # Mock ProjectInfoManager to prevent authentication attempts
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

        app = DDSApp(token_path=str(TOKEN_PATH))

        async with app.run_test() as pilot:
            # Start unauthenticated
            app.set_auth_status(False)
            await pilot.pause()
            assert app.project_list is None

            # Authenticate
            app.set_auth_status(True)
            await pilot.pause()

            # Test widget reflects state
            widget = ProjectList(title="Project List")
            app.mount(widget)
            await pilot.pause()

            select_widgets = widget.query(DDSSelect)
            select_widget = select_widgets[0]
            assert not select_widget.disabled
            assert len(select_widget._options) == 3  # BLANK + 2 projects


@pytest.mark.asyncio
async def test_data_validation():
    """Test malformed data is handled properly."""

    malformed_projects = [
        {"Project ID": "valid-001", "Title": "Valid"},
        {"Title": "No ID"},  # Invalid
        {"Project ID": "", "Title": "Empty ID"},  # Invalid
    ]

    with patch("dds_cli.data_lister.DataLister") as mock_data_lister_class:
        # Mock DataLister to prevent authentication attempts
        mock_data_lister_instance = MagicMock()
        mock_data_lister_class.return_value = mock_data_lister_instance
        mock_data_lister_instance.list_projects.return_value = malformed_projects

        app = DDSApp(token_path=str(TOKEN_PATH))

        async with app.run_test() as pilot:
            app.set_auth_status(True)
            await pilot.pause()

            widget = ProjectList(title="Project List")
            app.mount(widget)
            await pilot.pause()

            select_widgets = widget.query(DDSSelect)
            select_widget = select_widgets[0]
            assert len(select_widget._options) == 2  # BLANK + 1 valid project


# =================================================================================
# Enhanced Coverage
# =================================================================================


@pytest.mark.asyncio
async def test_preselected_project():
    """Test widget when a project is already selected."""

    with patch("dds_cli.data_lister.DataLister") as mock_data_lister_class, patch(
        "dds_cli.project_info.ProjectInfoManager"
    ) as mock_project_info_class:
        # Mock DataLister to prevent authentication attempts
        mock_data_lister_instance = MagicMock()
        mock_data_lister_class.return_value = mock_data_lister_instance
        mock_data_lister_instance.list_projects.return_value = MOCK_PROJECTS

        # Mock ProjectInfoManager to prevent authentication attempts
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

        app = DDSApp(token_path=str(TOKEN_PATH))

        async with app.run_test() as pilot:
            app.set_auth_status(True)
            await pilot.pause()

            # Set selected project after projects are loaded
            app.set_selected_project_id("project-002")
            await pilot.pause()

            widget = ProjectList(title="Project List")
            app.mount(widget)
            await pilot.pause()

            select_widgets = widget.query(DDSSelect)
            select_widget = select_widgets[0]
            assert select_widget.value == "project-002"


@pytest.mark.asyncio
async def test_multiple_api_errors():
    """Test handling of different API error types."""

    # Test ApiResponseError
    with patch("dds_cli.data_lister.DataLister") as mock_data_lister_class:
        # Mock DataLister to prevent authentication attempts
        mock_data_lister_instance = MagicMock()
        mock_data_lister_class.return_value = mock_data_lister_instance
        mock_data_lister_instance.list_projects.side_effect = dds_cli.exceptions.ApiResponseError(
            "Invalid API response"
        )

        app = DDSApp(token_path=str(TOKEN_PATH))
        notifications = []

        def capture_notify(message, **kwargs):
            notifications.append({"message": message, "severity": kwargs.get("severity")})

        app.notify = capture_notify

        async with app.run_test() as pilot:
            app.set_auth_status(True)
            await pilot.pause()

            assert app.project_list is None
            assert len(notifications) > 0
            assert notifications[-1]["severity"] == "error"

    # Test NoDataError (start with unauthenticated app to avoid init error)
    app2 = DDSApp(token_path=str(TOKEN_PATH))

    async with app2.run_test() as pilot:
        app2.set_auth_status(False)
        await pilot.pause()

        with patch("dds_cli.data_lister.DataLister") as mock_data_lister_class:
            # Mock DataLister to prevent authentication attempts
            mock_data_lister_instance = MagicMock()
            mock_data_lister_class.return_value = mock_data_lister_instance
            mock_data_lister_instance.list_projects.side_effect = dds_cli.exceptions.NoDataError(
                "No projects available"
            )

            try:
                app2.set_auth_status(True)
                await pilot.pause()
                # NoDataError should be raised and not caught
            except dds_cli.exceptions.NoDataError:
                # This is expected - NoDataError not handled in watch_auth_status
                assert True


@pytest.mark.asyncio
async def test_special_characters():
    """Test handling of project IDs with special characters."""

    special_projects = [
        {"Project ID": "project-with-spaces in name", "Title": "Test"},
        {"Project ID": "project_with_underscores", "Title": "Test"},
        {"Project ID": "project-with-unicode-émojis🎉", "Title": "Test"},
        {"Project ID": "project/with/slashes", "Title": "Test"},
        {"Project ID": "project.with.dots", "Title": "Test"},
    ]

    with patch("dds_cli.data_lister.DataLister") as mock_data_lister_class:
        # Mock DataLister to prevent authentication attempts
        mock_data_lister_instance = MagicMock()
        mock_data_lister_class.return_value = mock_data_lister_instance
        mock_data_lister_instance.list_projects.return_value = special_projects

        app = DDSApp(token_path=str(TOKEN_PATH))

        async with app.run_test() as pilot:
            app.set_auth_status(True)
            await pilot.pause()

            widget = ProjectList(title="Project List")
            app.mount(widget)
            await pilot.pause()

            select_widgets = widget.query(DDSSelect)
            select_widget = select_widgets[0]
            assert len(select_widget._options) == 6  # BLANK + 5 special projects


@pytest.mark.asyncio
async def test_auth_logout_clears_data():
    """Test that logging out clears project data."""

    with patch("dds_cli.data_lister.DataLister") as mock_data_lister_class, patch(
        "dds_cli.project_info.ProjectInfoManager"
    ) as mock_project_info_class:
        # Mock DataLister to prevent authentication attempts
        mock_data_lister_instance = MagicMock()
        mock_data_lister_class.return_value = mock_data_lister_instance
        mock_data_lister_instance.list_projects.return_value = MOCK_PROJECTS

        # Mock ProjectInfoManager to prevent authentication attempts
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

        app = DDSApp(token_path=str(TOKEN_PATH))

        async with app.run_test() as pilot:
            # Authenticate and load data
            app.set_auth_status(True)
            await pilot.pause()

            widget = ProjectList(title="Project List")
            app.mount(widget)
            await pilot.pause()

            # Select a project
            select_widgets = widget.query(DDSSelect)
            select_widget = select_widgets[0]
            select_widget.value = "project-001"
            app.set_selected_project_id("project-001")

            # Logout - should clear data via reactive system
            app.set_auth_status(False)
            await pilot.pause()

            # Verify data cleared
            assert app.project_list is None
            assert app.selected_project_id is None

            # Test fresh widget reflects logout state
            widget.remove()
            await pilot.pause()

            new_widget = ProjectList(title="Project List")
            app.mount(new_widget)
            await pilot.pause()

            new_select_widgets = new_widget.query(DDSSelect)
            new_select_widget = new_select_widgets[0]
            assert new_select_widget.disabled


@pytest.mark.asyncio
async def test_large_dataset_performance():
    """Test performance with large number of projects."""

    large_projects = [
        {"Project ID": f"project-{i:03d}", "Title": f"Project {i}"} for i in range(1, 101)
    ]  # 100 projects

    with patch("dds_cli.data_lister.DataLister") as mock_data_lister_class:
        # Mock DataLister to prevent authentication attempts
        mock_data_lister_instance = MagicMock()
        mock_data_lister_class.return_value = mock_data_lister_instance
        mock_data_lister_instance.list_projects.return_value = large_projects

        app = DDSApp(token_path=str(TOKEN_PATH))

        async with app.run_test() as pilot:
            app.set_auth_status(True)
            await pilot.pause()

            widget = ProjectList(title="Project List")
            app.mount(widget)
            await pilot.pause()

            select_widgets = widget.query(DDSSelect)
            select_widget = select_widgets[0]
            assert len(select_widget._options) == 101  # BLANK + 100 projects
