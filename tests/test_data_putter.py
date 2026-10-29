"""Tests for the data_putter module."""

# IMPORTS ######################################################################

import json
import logging
import pathlib
from unittest.mock import MagicMock, patch

import pytest

from dds_cli import exceptions
from dds_cli.data_putter import DataPutter
from dds_cli.file_handler import FileHandler

# HELPERS ######################################################################


def _failed_entry(failed_op):
    """Build an entry as saved in dds_failed_delivery.json for a file which failed in `failed_op`."""
    return {"path_remote": "remote/path", "status": {"failed_op": failed_op}}


def _prepare_data_putter(log_file, failed):
    """Mock a DataPutter instance with a failed delivery log containing `failed`."""
    # Create DataPutter instance without running __init__
    dp = DataPutter.__new__(DataPutter)
    dp.project = "test-project"
    dp.token = {}
    dp.failed_delivery_log = log_file
    dp.retry_added_any_file = False

    # Mark the files as failed, as done during the upload
    dp.status = {
        file: {"cancel": True, "failed_op": entry["status"]["failed_op"], "message": "failed"}
        for file, entry in failed.items()
    }

    # Create the failed delivery log
    log_file.write_text(json.dumps(failed, indent=4), encoding="utf-8")
    return dp


def _mock_retry_response(monkeypatch, files_added, message=None):
    """Make the API call in retry_add_file_db return `files_added` and `message`."""
    monkeypatch.setattr(
        "dds_cli.utils.perform_request",
        lambda *_, **__: ({"files_added": files_added, "message": message or {}}, None),
    )


# TESTS ########################################################################


@patch("dds_cli.data_putter.Progress")
@patch("dds_cli.data_putter.dds_cli.utils.delete_folder")
@patch("dds_cli.data_putter.fhl.LocalFileHandler")
@patch("dds_cli.data_putter.base.user.User")
@patch("dds_cli.data_putter.base.DDSBaseClass._DDSBaseClass__get_safespring_keys")
@patch("dds_cli.data_putter.base.DDSBaseClass._DDSBaseClass__get_project_keys")
def test_init_data_putter_all_files_already_uploaded_deletion_fails(
    mock_get_keys,
    mock_get_s3,
    mock_user_class,
    mock_filehandler_class,
    mock_delete_folder,
    mock_progress,
):
    """Test DataPutter initialization when all files are already uploaded and deletion fails.

    This test verifies that when files are already uploaded and the temporary directory
    deletion fails (e.g., due to log file still being written), the proper error message
    is still shown to the user instead of raising an OSError.
    """
    # Setup mocks for authentication
    mock_user_instance = MagicMock()
    mock_user_instance.token_dict = {"Authorization": "Bearer test_token"}
    mock_user_class.return_value = mock_user_instance

    # Mock S3 and keys
    mock_get_s3.return_value = MagicMock()
    mock_get_keys.return_value = (None, "public_key")

    # Mock Progress context manager
    mock_progress_instance = MagicMock()
    mock_progress_instance.__enter__.return_value = mock_progress_instance
    mock_progress_instance.__exit__.return_value = False
    mock_progress_instance.add_task.return_value = 1
    mock_progress.return_value = mock_progress_instance

    # Mock filehandler with empty data (all files already uploaded)
    mock_filehandler = MagicMock()
    mock_filehandler.data = {}  # Empty - all files already uploaded
    mock_filehandler.check_previous_upload.return_value = []  # No files in DB
    mock_filehandler.create_upload_status_dict.return_value = {}
    mock_filehandler_class.return_value = mock_filehandler

    # Mock staging directory
    mock_staging_dir = MagicMock()
    mock_temp_dir = MagicMock()
    mock_temp_dir.is_dir.return_value = True
    mock_staging_dir.directories = {
        "ROOT": mock_temp_dir,
        "FILES": MagicMock(),
        "LOGS": MagicMock(),
    }

    # Make delete_folder raise OSError (simulating log file still open)
    mock_delete_folder.side_effect = OSError("[Errno 39] Directory not empty: '/path/to/logs'")

    # Create DataPutter instance - should still raise UploadError despite deletion failure
    with pytest.raises(exceptions.UploadError) as exc_info:
        DataPutter(
            project="test-project",
            staging_dir=mock_staging_dir,
            source=("test_file.txt",),
            method="put",
        )

    # Verify the error message is still shown correctly
    assert "already been uploaded" in str(exc_info.value)
    assert "--overwrite" in str(exc_info.value)

    # Verify delete_folder was called (even though it failed)
    mock_delete_folder.assert_called_once_with(mock_temp_dir)


def test_retry_add_file_db_deletes_log_when_all_files_added(monkeypatch, tmp_path):
    """Test that the failed delivery log is deleted when the retry adds all failed files."""
    log_file = tmp_path / "dds_failed_delivery.json"

    # Mock DataPutter instance with helper
    putter = _prepare_data_putter(
        log_file,
        failed={"file1": _failed_entry("add_file_db"), "file2": _failed_entry("add_file_db")},
    )
    _mock_retry_response(monkeypatch, files_added=["file1", "file2"])

    # Call the DataPutter.retry_add_file_db method
    putter.retry_add_file_db()

    # Verify that the log is deleted and the files are no longer marked as failed
    assert not log_file.exists()
    assert putter.retry_added_any_file
    assert putter.status["file1"]["cancel"] is False
    assert putter.status["file2"]["cancel"] is False


def test_retry_add_file_db_keeps_entries_with_other_failed_op(monkeypatch, tmp_path):
    """Test that entries which did not fail in add_file_db are kept in a valid json file."""
    log_file = tmp_path / "dds_failed_delivery.json"

    # Mock DataPutter instance with helper
    putter = _prepare_data_putter(
        log_file,
        failed={"file1": _failed_entry("add_file_db"), "file2": _failed_entry("put")},
    )
    _mock_retry_response(monkeypatch, files_added=["file1"])

    # Call the DataPutter.retry_add_file_db method
    putter.retry_add_file_db()

    # Verify that only the put entry is left
    # json.loads fails if the shrunk file is not truncated
    assert json.loads(log_file.read_text(encoding="utf-8")) == {"file2": _failed_entry("put")}
    assert putter.status["file2"]["cancel"] is True


def test_retry_add_file_db_keeps_files_not_added(monkeypatch, tmp_path):
    """Test that files which the retry could not add to the database are kept in the log."""
    log_file = tmp_path / "dds_failed_delivery.json"

    # Mock DataPutter instance with helper
    putter = _prepare_data_putter(
        log_file,
        failed={"file1": _failed_entry("add_file_db"), "file2": _failed_entry("add_file_db")},
    )
    _mock_retry_response(
        monkeypatch, files_added=["file1"], message={"file2": {"error": "File not found in S3"}}
    )

    # Call the DataPutter.retry_add_file_db method
    putter.retry_add_file_db()

    # Verify that only the file which was not added is left
    assert json.loads(log_file.read_text(encoding="utf-8")) == {
        "file2": _failed_entry("add_file_db")
    }


def test_retry_add_file_db_api_error_keeps_log(monkeypatch, tmp_path):
    """Test that the log is left untouched if the retry request fails."""
    log_file = tmp_path / "dds_failed_delivery.json"

    # Mock DataPutter instance with helper
    putter = _prepare_data_putter(log_file, failed={"file1": _failed_entry("add_file_db")})
    content_before = log_file.read_text(encoding="utf-8")

    # Helper function to replace perform_request and raise an API error
    def fake_perform_request(*_, **__):
        raise exceptions.ApiResponseError("Failed to add missing files")

    monkeypatch.setattr("dds_cli.utils.perform_request", fake_perform_request)

    # Call the DataPutter.retry_add_file_db method
    with pytest.raises(exceptions.ApiResponseError):
        putter.retry_add_file_db()

    # Verify that the log is unchanged
    assert log_file.read_text(encoding="utf-8") == content_before


def test_remove_entries_from_error_file_deletion_fails(monkeypatch, tmp_path, caplog):
    """Test that a failure to delete the log is logged as a warning instead of raised."""
    log_file = tmp_path / "dds_failed_delivery.json"
    log_file.write_text(json.dumps({"file1": _failed_entry("add_file_db")}), encoding="utf-8")

    # Helper function to replace Path.unlink and raise an OSError
    def fake_unlink(*_, **__):
        raise OSError("File is in use")

    monkeypatch.setattr(pathlib.Path, "unlink", fake_unlink)

    # Call the FileHandler.remove_entries_from_error_file method
    with caplog.at_level(logging.WARNING, logger="dds_cli.file_handler"):
        FileHandler.remove_entries_from_error_file(log_file=log_file, files=["file1"])

    # Verify that the log still exists and the error is logged
    assert log_file.exists()
    assert ("dds_cli.file_handler", logging.WARNING, "File is in use") in caplog.record_tuples
