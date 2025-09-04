"""GUI tests for Project Information widget using reactive patterns."""

import pathlib
from unittest.mock import patch, MagicMock
import pytest

from dds_cli.dds_gui.app import DDSApp
from dds_cli.dds_gui.pages.project_information.project_information import (
    ProjectInformation,
    ProjectInformationTable,
)
from dds_cli.dds_gui.models.project_information import (
    ProjectInformationData,
    ProjectInformationDataTable,
)
from dds_cli.dds_gui.types.dds_status_types import DDSStatus
import dds_cli.exceptions

TOKEN_PATH = pathlib.Path("custom") / "token" / "path"

# Test data
MOCK_PROJECT_INFO_DATA = {
    "Title": "Test Project",
    "Description": "A test project for unit testing",
    "Status": "Available",
    "Created by": "test_user@example.com",
    "Last updated": "2024-01-15 10:30:00",
    "Size": 1000,
    "PI": "Dr. Test Investigator",
}

MOCK_PROJECT_INFO_DATA_WITH_NONE = {
    "Title": "Test Project",
    "Description": "A test project for unit testing",
    "Status": "In Progress",
    "Created by": None,
    "Last updated": None,
    "Size": None,
    "PI": None,
}


# =================================================================================
# Model Tests - ProjectInformationDataTable
# =================================================================================


def test_project_information_data_table_from_dict_valid():
    """Test ProjectInformationDataTable.from_dict with valid data."""
    data_table = ProjectInformationDataTable.from_dict(MOCK_PROJECT_INFO_DATA)

    assert data_table.status == DDSStatus.AVAILABLE
    assert data_table.created_by == "test_user@example.com"
    assert data_table.last_updated == "2024-01-15 10:30:00"
    assert data_table.size == "1.0 KB"
    assert data_table.pi == "Dr. Test Investigator"


def test_project_information_data_table_from_dict_with_none_values():
    """Test ProjectInformationDataTable.from_dict with None values."""
    data_table = ProjectInformationDataTable.from_dict(MOCK_PROJECT_INFO_DATA_WITH_NONE)

    assert data_table.status == DDSStatus.IN_PROGRESS
    assert data_table.created_by == "N/A"
    assert data_table.last_updated == "N/A"
    assert data_table.size == "N/A"
    assert data_table.pi == "N/A"


def test_project_information_data_table_from_dict_missing_field():
    """Test ProjectInformationDataTable.from_dict with missing required field."""
    incomplete_data = {
        "Title": "Test Project",
        "Description": "A test project",
        "Status": "Available",
        "Created by": "test_user",
        # Missing "Last updated", "Size", "PI"
    }

    with pytest.raises(ValueError, match="Missing required field: Last updated"):
        ProjectInformationDataTable.from_dict(incomplete_data)


def test_project_information_data_table_from_dict_empty_dict():
    """Test ProjectInformationDataTable.from_dict with empty dictionary."""
    with pytest.raises(ValueError, match="Missing required field: Status"):
        ProjectInformationDataTable.from_dict({})


def test_project_information_data_table_from_dict_invalid_status():
    """Test ProjectInformationDataTable.from_dict with invalid status."""
    invalid_data = MOCK_PROJECT_INFO_DATA.copy()
    invalid_data["Status"] = "InvalidStatus"

    with pytest.raises(ValueError):
        ProjectInformationDataTable.from_dict(invalid_data)


# =================================================================================
# Model Tests - ProjectInformationData
# =================================================================================


def test_project_information_data_from_dict_valid():
    """Test ProjectInformationData.from_dict with valid data."""
    project_data = ProjectInformationData.from_dict(MOCK_PROJECT_INFO_DATA)

    assert project_data.name == "Test Project"
    assert project_data.description == "A test project for unit testing"
    assert isinstance(project_data.information_table, ProjectInformationDataTable)
    assert project_data.information_table.status == DDSStatus.AVAILABLE


def test_project_information_data_from_dict_with_none_values():
    """Test ProjectInformationData.from_dict with None values."""
    project_data = ProjectInformationData.from_dict(MOCK_PROJECT_INFO_DATA_WITH_NONE)

    assert project_data.name == "Test Project"
    assert project_data.description == "A test project for unit testing"
    assert project_data.information_table.created_by == "N/A"


def test_project_information_data_from_dict_missing_title():
    """Test ProjectInformationData.from_dict with missing title."""
    incomplete_data = MOCK_PROJECT_INFO_DATA.copy()
    del incomplete_data["Title"]

    with pytest.raises(ValueError, match="Missing required field: Title"):
        ProjectInformationData.from_dict(incomplete_data)


def test_project_information_data_from_dict_missing_description():
    """Test ProjectInformationData.from_dict with missing description."""
    incomplete_data = MOCK_PROJECT_INFO_DATA.copy()
    del incomplete_data["Description"]

    with pytest.raises(ValueError, match="Missing required field: Description"):
        ProjectInformationData.from_dict(incomplete_data)


def test_project_information_data_from_dict_empty_title_description():
    """Test ProjectInformationData.from_dict with empty title and description."""
    data_with_empty = MOCK_PROJECT_INFO_DATA.copy()
    data_with_empty["Title"] = None
    data_with_empty["Description"] = None

    project_data = ProjectInformationData.from_dict(data_with_empty)
    assert project_data.name == "N/A"
    assert project_data.description == "N/A"


# =================================================================================
# Widget Tests - ProjectInformationTable
# =================================================================================


@pytest.mark.asyncio
async def test_project_information_table_compose():
    """Test ProjectInformationTable widget composition."""
    data_table = ProjectInformationDataTable.from_dict(MOCK_PROJECT_INFO_DATA)
    table_widget = ProjectInformationTable(data_table)

    with patch("dds_cli.data_lister.DataLister") as mock_data_lister_class:
        mock_data_lister_instance = MagicMock()
        mock_data_lister_class.return_value = mock_data_lister_instance
        mock_data_lister_instance.list_projects.return_value = []

        app = DDSApp(token_path=str(TOKEN_PATH))

        async with app.run_test() as pilot:
            app.mount(table_widget)
            await pilot.pause()

            # Check that all expected elements are present
            status_chips = app.query("DDSStatusChip")
            assert len(status_chips) == 1
            assert status_chips[0].status == DDSStatus.AVAILABLE

            # Check all static text elements
            static_elements = app.query("Static")
            assert len(static_elements) >= 8  # 4 keys + 4 values

            # Verify specific content
            created_by_elements = [
                elem for elem in static_elements if elem.renderable == "test_user@example.com"
            ]
            assert len(created_by_elements) == 1

            pi_elements = [
                elem for elem in static_elements if elem.renderable == "Dr. Test Investigator"
            ]
            assert len(pi_elements) == 1


@pytest.mark.asyncio
async def test_project_information_table_with_none_values():
    """Test ProjectInformationTable widget with None values."""
    data_table = ProjectInformationDataTable.from_dict(MOCK_PROJECT_INFO_DATA_WITH_NONE)
    table_widget = ProjectInformationTable(data_table)

    with patch("dds_cli.data_lister.DataLister") as mock_data_lister_class:
        mock_data_lister_instance = MagicMock()
        mock_data_lister_class.return_value = mock_data_lister_instance
        mock_data_lister_instance.list_projects.return_value = []

        app = DDSApp(token_path=str(TOKEN_PATH))

        async with app.run_test() as pilot:
            app.mount(table_widget)
            await pilot.pause()

            # Check that N/A values are displayed
            static_elements = app.query("Static")
            na_elements = [elem for elem in static_elements if elem.renderable == "N/A"]
            assert len(na_elements) == 4  # created_by, last_updated, size, pi

            # Check size display (should show "N/A" without "B")
            size_elements = [elem for elem in static_elements if "N/A" in str(elem.renderable)]
            assert len(size_elements) >= 1


@pytest.mark.asyncio
async def test_project_information_table_size_display():
    """Test ProjectInformationTable size display logic."""
    # Test with valid size
    data_with_size = MOCK_PROJECT_INFO_DATA.copy()
    data_with_size["Size"] = "2048"  # Use numeric value, will be formatted to "2.0 KB"
    data_table = ProjectInformationDataTable.from_dict(data_with_size)
    table_widget = ProjectInformationTable(data_table)

    with patch("dds_cli.data_lister.DataLister") as mock_data_lister_class:
        mock_data_lister_instance = MagicMock()
        mock_data_lister_class.return_value = mock_data_lister_instance
        mock_data_lister_instance.list_projects.return_value = []

        app = DDSApp(token_path=str(TOKEN_PATH))

        async with app.run_test() as pilot:
            app.mount(table_widget)
            await pilot.pause()

            # Check that size is displayed with "B" suffix
            static_elements = app.query("Static")
            size_elements = [elem for elem in static_elements if "2.0 KB" in str(elem.renderable)]
            assert len(size_elements) == 1


# =================================================================================
# Widget Tests - ProjectInformation
# =================================================================================


@pytest.mark.asyncio
async def test_project_information_with_data():
    """Test ProjectInformation widget with project data."""
    project_data = ProjectInformationData.from_dict(MOCK_PROJECT_INFO_DATA)

    with patch("dds_cli.data_lister.DataLister") as mock_data_lister_class:
        mock_data_lister_instance = MagicMock()
        mock_data_lister_class.return_value = mock_data_lister_instance
        mock_data_lister_instance.list_projects.return_value = []

        app = DDSApp(token_path=str(TOKEN_PATH))

        async with app.run_test() as pilot:
            # Set project information in app state
            app.project_information = project_data
            await pilot.pause()

            widget = ProjectInformation(title="Project Information")
            app.mount(widget)
            await pilot.pause()

            # Check that project information is displayed
            title_elements = app.query("#project-title")
            assert len(title_elements) >= 1
            assert "Test Project" in str(title_elements[0].renderable)

            description_elements = app.query("#project-description")
            assert len(description_elements) >= 1
            assert "A test project for unit testing" in str(description_elements[0].renderable)

            # Check that table is present
            table_elements = app.query("#project-information-table")
            assert len(table_elements) >= 1


@pytest.mark.asyncio
async def test_project_information_without_data():
    """Test ProjectInformation widget without project data."""
    with patch("dds_cli.data_lister.DataLister") as mock_data_lister_class:
        mock_data_lister_instance = MagicMock()
        mock_data_lister_class.return_value = mock_data_lister_instance
        mock_data_lister_instance.list_projects.return_value = []

        app = DDSApp(token_path=str(TOKEN_PATH))

        async with app.run_test() as pilot:
            # Ensure no project information is set
            app.project_information = None
            await pilot.pause()

            widget = ProjectInformation(title="Project Information")
            app.mount(widget)
            await pilot.pause()

            # Check that "No project selected" message is displayed
            text_elements = app.query("DDSTextItem")
            no_project_elements = [
                elem for elem in text_elements if "No project selected" in str(elem.renderable)
            ]
            assert len(no_project_elements) >= 1

            # Check that no table is present
            table_elements = app.query("#project-information-table")
            assert len(table_elements) == 0


@pytest.mark.asyncio
async def test_project_information_reactive_updates():
    """Test ProjectInformation widget reactive updates."""
    with patch("dds_cli.data_lister.DataLister") as mock_data_lister_class:
        mock_data_lister_instance = MagicMock()
        mock_data_lister_class.return_value = mock_data_lister_instance
        mock_data_lister_instance.list_projects.return_value = []

        app = DDSApp(token_path=str(TOKEN_PATH))

        async with app.run_test() as pilot:
            widget = ProjectInformation(title="Project Information")
            app.mount(widget)
            await pilot.pause()

            # Initially no data
            text_elements = app.query("DDSTextItem")
            no_project_elements = [
                elem for elem in text_elements if "No project selected" in str(elem.renderable)
            ]
            assert len(no_project_elements) >= 1

            # Add project data
            project_data = ProjectInformationData.from_dict(MOCK_PROJECT_INFO_DATA)
            app.project_information = project_data
            await pilot.pause()

            # Check that content updated
            title_elements = app.query("#project-title")
            assert len(title_elements) >= 1
            assert "Test Project" in str(title_elements[0].renderable)

            # Remove project data
            app.project_information = None
            await pilot.pause()

            # Check that it reverted to "No project selected"
            text_elements = app.query("DDSTextItem")
            no_project_elements = [
                elem for elem in text_elements if "No project selected" in str(elem.renderable)
            ]
            assert len(no_project_elements) >= 1


# =================================================================================
# Integration Tests - App State Management
# =================================================================================


@pytest.mark.asyncio
async def test_fetch_project_information_success():
    """Test successful project information fetching."""
    with patch("dds_cli.data_lister.DataLister") as mock_data_lister_class, patch(
        "dds_cli.project_info.ProjectInfoManager"
    ) as mock_project_info_class:

        mock_data_lister_instance = MagicMock()
        mock_data_lister_class.return_value = mock_data_lister_instance
        mock_data_lister_instance.list_projects.return_value = []

        mock_project_info_instance = MagicMock()
        mock_project_info_class.return_value = mock_project_info_instance
        mock_project_info_instance.get_project_info.return_value = MOCK_PROJECT_INFO_DATA

        app = DDSApp(token_path=str(TOKEN_PATH))

        async with app.run_test() as pilot:
            app.set_auth_status(True)
            await pilot.pause()

            # Fetch project information
            app.fetch_project_information("test-project-id")
            await pilot.pause()

            # Verify project information was set
            assert app.project_information is not None
            assert app.project_information.name == "Test Project"
            assert app.project_information.description == "A test project for unit testing"
            assert app.project_information.information_table.status == DDSStatus.AVAILABLE


@pytest.mark.asyncio
async def test_fetch_project_information_api_error():
    """Test project information fetching with API error."""
    with patch("dds_cli.data_lister.DataLister") as mock_data_lister_class, patch(
        "dds_cli.project_info.ProjectInfoManager"
    ) as mock_project_info_class:

        mock_data_lister_instance = MagicMock()
        mock_data_lister_class.return_value = mock_data_lister_instance
        mock_data_lister_instance.list_projects.return_value = []

        mock_project_info_instance = MagicMock()
        mock_project_info_class.return_value = mock_project_info_instance
        mock_project_info_instance.get_project_info.side_effect = (
            dds_cli.exceptions.ApiRequestError("Connection failed")
        )

        app = DDSApp(token_path=str(TOKEN_PATH))
        notifications = []

        def capture_notify(message, **kwargs):
            notifications.append({"message": message, "severity": kwargs.get("severity")})

        app.notify = capture_notify

        async with app.run_test() as pilot:
            app.set_auth_status(True)
            await pilot.pause()

            # Fetch project information
            app.fetch_project_information("test-project-id")
            await pilot.pause()

            # Verify error handling
            assert app.project_information is None
            assert len(notifications) > 0
            assert "Failed to fetch project information" in notifications[-1]["message"]
            assert notifications[-1]["severity"] == "error"


@pytest.mark.asyncio
async def test_fetch_project_information_response_error():
    """Test project information fetching with API response error."""
    with patch("dds_cli.data_lister.DataLister") as mock_data_lister_class, patch(
        "dds_cli.project_info.ProjectInfoManager"
    ) as mock_project_info_class:

        mock_data_lister_instance = MagicMock()
        mock_data_lister_class.return_value = mock_data_lister_instance
        mock_data_lister_instance.list_projects.return_value = []

        mock_project_info_instance = MagicMock()
        mock_project_info_class.return_value = mock_project_info_instance
        mock_project_info_instance.get_project_info.side_effect = (
            dds_cli.exceptions.ApiResponseError("Invalid response")
        )

        app = DDSApp(token_path=str(TOKEN_PATH))
        notifications = []

        def capture_notify(message, **kwargs):
            notifications.append({"message": message, "severity": kwargs.get("severity")})

        app.notify = capture_notify

        async with app.run_test() as pilot:
            app.set_auth_status(True)
            await pilot.pause()

            # Fetch project information
            app.fetch_project_information("test-project-id")
            await pilot.pause()

            # Verify error handling
            assert app.project_information is None
            assert len(notifications) > 0
            assert "Failed to fetch project information" in notifications[-1]["message"]


@pytest.mark.asyncio
async def test_fetch_project_information_dds_exception():
    """Test project information fetching with DDS CLI exception."""
    with patch("dds_cli.data_lister.DataLister") as mock_data_lister_class, patch(
        "dds_cli.project_info.ProjectInfoManager"
    ) as mock_project_info_class:

        mock_data_lister_instance = MagicMock()
        mock_data_lister_class.return_value = mock_data_lister_instance
        mock_data_lister_instance.list_projects.return_value = []

        mock_project_info_instance = MagicMock()
        mock_project_info_class.return_value = mock_project_info_instance
        mock_project_info_instance.get_project_info.side_effect = (
            dds_cli.exceptions.DDSCLIException("DDS error")
        )

        app = DDSApp(token_path=str(TOKEN_PATH))
        notifications = []

        def capture_notify(message, **kwargs):
            notifications.append({"message": message, "severity": kwargs.get("severity")})

        app.notify = capture_notify

        async with app.run_test() as pilot:
            app.set_auth_status(True)
            await pilot.pause()

            # Fetch project information
            app.fetch_project_information("test-project-id")
            await pilot.pause()

            # Verify error handling
            assert app.project_information is None
            assert len(notifications) > 0
            assert "Failed to fetch project information" in notifications[-1]["message"]


# =================================================================================
# Edge Cases and Error Handling Tests
# =================================================================================


def test_project_information_data_table_all_status_values():
    """Test ProjectInformationDataTable with all possible status values."""
    for status in DDSStatus:
        test_data = MOCK_PROJECT_INFO_DATA.copy()
        test_data["Status"] = status.value

        data_table = ProjectInformationDataTable.from_dict(test_data)
        assert data_table.status == status


def test_project_information_data_table_large_size():
    """Test ProjectInformationDataTable with large size value."""
    large_size_data = MOCK_PROJECT_INFO_DATA.copy()
    large_size_data["Size"] = "1000000000"  # 1.0GB

    data_table = ProjectInformationDataTable.from_dict(large_size_data)
    assert data_table.size == "1.0 GB"


def test_project_information_data_table_zero_size():
    """Test ProjectInformationDataTable with zero size."""
    zero_size_data = MOCK_PROJECT_INFO_DATA.copy()
    zero_size_data["Size"] = "0"

    data_table = ProjectInformationDataTable.from_dict(zero_size_data)
    assert data_table.size == "0.0 B"


def test_project_information_data_table_empty_strings():
    """Test ProjectInformationDataTable with empty string values."""
    empty_string_data = MOCK_PROJECT_INFO_DATA.copy()
    empty_string_data["Created by"] = ""
    empty_string_data["Last updated"] = ""
    empty_string_data["PI"] = ""

    data_table = ProjectInformationDataTable.from_dict(empty_string_data)
    assert data_table.created_by == "N/A"
    assert data_table.last_updated == "N/A"
    assert data_table.pi == "N/A"


def test_project_information_data_table_unicode_content():
    """Test ProjectInformationDataTable with unicode content."""
    unicode_data = MOCK_PROJECT_INFO_DATA.copy()
    unicode_data["Created by"] = "测试用户@example.com"
    unicode_data["PI"] = "Dr. José María"
    unicode_data["Description"] = "Projet de test avec caractères spéciaux"

    project_data = ProjectInformationData.from_dict(unicode_data)
    assert project_data.information_table.created_by == "测试用户@example.com"
    assert project_data.information_table.pi == "Dr. José María"
    assert project_data.description == "Projet de test avec caractères spéciaux"


# =================================================================================
# Full Integration Test
# =================================================================================


@pytest.mark.asyncio
async def test_full_project_information_workflow():
    """Test complete project information workflow from app state to UI display."""
    with patch("dds_cli.data_lister.DataLister") as mock_data_lister_class, patch(
        "dds_cli.project_info.ProjectInfoManager"
    ) as mock_project_info_class:

        mock_data_lister_instance = MagicMock()
        mock_data_lister_class.return_value = mock_data_lister_instance
        mock_data_lister_instance.list_projects.return_value = []

        mock_project_info_instance = MagicMock()
        mock_project_info_class.return_value = mock_project_info_instance
        mock_project_info_instance.get_project_info.return_value = MOCK_PROJECT_INFO_DATA

        app = DDSApp(token_path=str(TOKEN_PATH))

        async with app.run_test() as pilot:
            # Start unauthenticated
            app.set_auth_status(False)
            await pilot.pause()
            assert app.project_information is None

            # Authenticate
            app.set_auth_status(True)
            await pilot.pause()

            # Mount the widget
            widget = ProjectInformation(title="Project Information")
            app.mount(widget)
            await pilot.pause()

            # Initially no project information
            text_elements = app.query("DDSTextItem")
            no_project_elements = [
                elem for elem in text_elements if "No project selected" in str(elem.renderable)
            ]
            assert len(no_project_elements) >= 1

            # Fetch project information
            app.fetch_project_information("test-project-id")
            await pilot.pause()

            # Verify project information is displayed
            assert app.project_information is not None

            title_elements = app.query("#project-title")
            assert len(title_elements) >= 1
            assert "Test Project" in str(title_elements[0].renderable)

            description_elements = app.query("#project-description")
            assert len(description_elements) >= 1
            assert "A test project for unit testing" in str(description_elements[0].renderable)

            # Verify table is present and functional
            table_elements = app.query("#project-information-table")
            assert len(table_elements) >= 1

            status_chips = app.query("DDSStatusChip")
            assert len(status_chips) >= 1
            assert status_chips[0].status == DDSStatus.AVAILABLE

            # Test logout clears data
            app.set_auth_status(False)
            await pilot.pause()

            # Widget should still show the data until recomposed
            # (This tests the reactive behavior)
            assert app.project_information is not None  # Data persists until widget recomposes
