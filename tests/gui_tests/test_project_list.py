"""GUI tests for Project List widget using reactive patterns."""

import pathlib
from unittest.mock import patch, MagicMock
import pytest

from dds_cli.dds_gui.app import DDSApp
from dds_cli.dds_gui.pages.project_list.project_list import ProjectList
from dds_cli.dds_gui.components.dds_select import DDSSelect
from dds_cli.dds_gui.models.project import ProjectList as ProjectListModel
from textual.widgets import Label
import dds_cli.exceptions

TOKEN_PATH = pathlib.Path("custom") / "token" / "path"

# Test data
MOCK_PROJECTS = [
    {"Project ID": "project-001", "Title": "Project Alpha", "Access": True},
    {"Project ID": "project-002", "Title": "Project Beta", "Access": True},
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
            app.project_list = ProjectListModel.from_dict(MOCK_PROJECTS)
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


# Removed test_unauthenticated_state() - covered by test_async_project_loading.py::test_unauthenticated_user_sees_auth_message()


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
            app.project_list = ProjectListModel.from_dict(MOCK_PROJECTS)
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
            app.project_list = ProjectListModel.from_dict(MOCK_PROJECTS)
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
            app.project_list = ProjectListModel.from_dict([])
            await pilot.pause()

            widget = ProjectList(title="Project List")
            app.mount(widget)
            await pilot.pause()

            # Should show "No projects found" message for authenticated user with empty project list
            labels = widget.query(Label)
            no_projects_labels = [
                label for label in labels if "no projects" in str(label.render().plain).lower()
            ]
            assert len(no_projects_labels) == 1, "Should show no projects found message"

            # Should not show project selector when no projects
            select_widgets = widget.query(DDSSelect)
            assert (
                len(select_widgets) == 0
            ), "Should not show project selector when no projects found"


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


# Removed test_auth_state_changes() - covered by test_async_project_loading.py::test_projects_load_after_authentication()


@pytest.mark.asyncio
async def test_data_validation():
    """Test malformed data is handled properly."""

    malformed_projects = [
        {"Project ID": "valid-001", "Title": "Valid", "Access": True},
        {"Title": "No ID"},  # Invalid - will be skipped
        {"Project ID": "", "Title": "Empty ID", "Access": True},  # Invalid - will be skipped
    ]

    with patch("dds_cli.data_lister.DataLister") as mock_data_lister_class:
        # Mock DataLister to prevent authentication attempts
        mock_data_lister_instance = MagicMock()
        mock_data_lister_class.return_value = mock_data_lister_instance
        mock_data_lister_instance.list_projects.return_value = malformed_projects

        app = DDSApp(token_path=str(TOKEN_PATH))

        async with app.run_test() as pilot:
            app.set_auth_status(True)
            # ProjectList.from_dict() now automatically filters invalid projects
            app.project_list = ProjectListModel.from_dict(malformed_projects)
            await pilot.pause()

            widget = ProjectList(title="Project List")
            app.mount(widget)
            await pilot.pause()

            # Should show project selector with only valid projects
            select_widgets = widget.query(DDSSelect)
            # Only 1 valid project should remain after filtering
            assert len(select_widgets) == 1, "Should show project selector"
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
            app.project_list = ProjectListModel.from_dict(MOCK_PROJECTS)
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

            # Set up notification capture
            notifications2 = []

            def capture_notify2(message, **kwargs):
                notifications2.append({"message": message, "severity": kwargs.get("severity")})

            app2.notify = capture_notify2

            app2.set_auth_status(True)
            await pilot.pause()

            # NoDataError should be handled gracefully and show error notification
            assert app2.project_list is None, "Project list should be None after NoDataError"
            assert len(notifications2) > 0, "Should show error notification for NoDataError"
            assert (
                notifications2[-1]["severity"] == "error"
            ), "Should show error severity for NoDataError"


@pytest.mark.asyncio
async def test_special_characters():
    """Test handling of project IDs with special characters."""

    special_projects = [
        {"Project ID": "project-with-spaces in name", "Title": "Test", "Access": True},
        {"Project ID": "project_with_underscores", "Title": "Test", "Access": True},
        {"Project ID": "project-with-unicode-émojis🎉", "Title": "Test", "Access": True},
        {"Project ID": "project/with/slashes", "Title": "Test", "Access": True},
        {"Project ID": "project.with.dots", "Title": "Test", "Access": True},
    ]

    with patch("dds_cli.data_lister.DataLister") as mock_data_lister_class:
        # Mock DataLister to prevent authentication attempts
        mock_data_lister_instance = MagicMock()
        mock_data_lister_class.return_value = mock_data_lister_instance
        mock_data_lister_instance.list_projects.return_value = special_projects

        app = DDSApp(token_path=str(TOKEN_PATH))

        async with app.run_test() as pilot:
            app.set_auth_status(True)
            app.project_list = ProjectListModel.from_dict(special_projects)
            await pilot.pause()

            widget = ProjectList(title="Project List")
            app.mount(widget)
            await pilot.pause()

            select_widgets = widget.query(DDSSelect)
            select_widget = select_widgets[0]
            assert len(select_widget._options) == 6  # BLANK + 5 special projects


# Removed test_auth_logout_clears_data() - covered by test_async_project_loading.py::test_loading_state_cleared_on_logout()


@pytest.mark.asyncio
async def test_large_dataset_performance():
    """Test performance with large number of projects."""

    large_projects = [
        {"Project ID": f"project-{i:03d}", "Title": f"Project {i}", "Access": True}
        for i in range(1, 101)
    ]  # 100 projects

    with patch("dds_cli.data_lister.DataLister") as mock_data_lister_class:
        # Mock DataLister to prevent authentication attempts
        mock_data_lister_instance = MagicMock()
        mock_data_lister_class.return_value = mock_data_lister_instance
        mock_data_lister_instance.list_projects.return_value = large_projects

        app = DDSApp(token_path=str(TOKEN_PATH))

        async with app.run_test() as pilot:
            app.set_auth_status(True)
            app.project_list = ProjectListModel.from_dict(large_projects)
            await pilot.pause()

            widget = ProjectList(title="Project List")
            app.mount(widget)
            await pilot.pause()

            select_widgets = widget.query(DDSSelect)
            select_widget = select_widgets[0]
            assert len(select_widget._options) == 101  # BLANK + 100 projects
