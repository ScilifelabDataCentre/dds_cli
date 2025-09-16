"""Test for the decorators."""

# refference: https://medium.com/analytics-vidhya/testing-python-decorators-3c5777e4524d
import pytest
from unittest.mock import patch, MagicMock

from dds_cli import custom_decorators

## TEST DATA
project_id = "test-123"

## DUMMY CLASS


# Dummy class to help with the decorator functions - add atributes to complete more tests
class Dummy:
    def __init__(self):
        self.project = project_id
        self.failed_table = None
        self.failed_files = None


##### HELPER FUNCTIONS AND DECORATORS


# the removal spinner relies on the function name, so we need to replace it dynamically
# https://stackoverflow.com/questions/10874432/possible-to-change-function-name-in-definition
def rename(newname):
    def decorator(f):
        f.__name__ = newname
        return f

    return decorator


###### TESTS


@pytest.mark.parametrize(
    "func_name, expected_printed_description",
    [
        ("remove_all", f"Successfully finished removing all files in project {project_id}"),
        ("remove_file", "Successfully finished removing file(s)"),
        ("remove_folder", "Successfully finished removing folder(s)"),
    ],
)
def test_removal_spinner_success(func_name, expected_printed_description):
    """Test the removal spinner decorator - success case."""

    @custom_decorators.removal_spinner
    @rename(func_name)
    def dummy_func(self):
        # gets renamed to func_name
        pass

    with patch("dds_cli.custom_decorators.Progress") as mock_progress, patch(
        "dds_cli.custom_decorators.dds_cli.utils.console"
    ) as mock_console:

        mock_progress_instance = MagicMock()
        mock_progress.return_value.__enter__.return_value = mock_progress_instance

        dummy = Dummy()
        dummy_func(dummy)

        # progress bar interactions happened
        mock_progress_instance.add_task.assert_called_once()
        mock_progress_instance.remove_task.assert_called_once()

        # console printed the success message
        printed = mock_console.print.call_args[0][0]
        assert expected_printed_description in printed


def test_removal_spinner_failed_table():
    """Test decorator prints failed_table and logs warning."""

    @custom_decorators.removal_spinner
    @rename("remove_file")
    def dummy_func(self):
        # gets renamed to remove_file
        pass

    with patch("dds_cli.custom_decorators.Progress"), patch(
        "dds_cli.custom_decorators.dds_cli.utils.console"
    ) as mock_console, patch("dds_cli.custom_decorators.LOG") as mock_log:

        dummy = Dummy()

        mock_console.height = 10
        # Fake a failed_table with row_count
        fake_table = MagicMock()
        fake_table.renderable.row_count = 3
        dummy.failed_table = fake_table

        dummy_func(dummy)

        # Console printed the failed table
        mock_console.print.assert_called_with(fake_table)

        # Should log a warning mentioning "removing file(s)"
        msg = mock_log.warning.call_args[0][0]
        assert "with errors" in msg.lower()


def test_removal_spinner_failed_files():
    """Test decorator prints failed_files dict with result message."""

    @custom_decorators.removal_spinner
    @rename("remove_folder")
    def dummy_func(self):
        # gets renamed to remove_folder
        pass

    with patch("dds_cli.custom_decorators.Progress"), patch(
        "dds_cli.custom_decorators.dds_cli.utils.console"
    ) as mock_console:

        dummy = Dummy()
        dummy.failed_files = {"some": "file"}
        dummy_func(dummy)

        # failed_files dict should have been updated
        assert "result" in dummy.failed_files
        assert "with errors" in dummy.failed_files["result"]

        # Console printed the failed_files dict
        mock_console.print.assert_called_with(dummy.failed_files)
