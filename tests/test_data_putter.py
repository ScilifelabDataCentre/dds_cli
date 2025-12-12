"""Tests for the data_putter module."""

# IMPORTS ######################################################################

from unittest.mock import MagicMock, patch

import pytest

from dds_cli import exceptions
from dds_cli.data_putter import DataPutter

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
