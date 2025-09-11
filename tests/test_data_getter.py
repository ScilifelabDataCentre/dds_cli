"""Tests for the data_getter module."""

# Imports

from types import SimpleNamespace
from unittest.mock import MagicMock

from dds_cli.data_getter import DataGetter
from dds_cli import constants

# Tests

def test_get_uses_timeout(monkeypatch, tmp_path):
    """Test that DataGetter.get uses the correct timeout values.
    
    monkeypatch is a pytest fixture that allows you to modify objects temporatily.
    tmp_path is a pytest fixture that provides a temporary directory.
    """
    # Create DataGetter instance without running __init__
    getter = DataGetter.__new__(DataGetter)

    # Mock filehandler with necessary data
    # Using SimpleNamespace because it allows you to create simple objects
    # with attributes without defining a custom class 
    # Here we use it to mock the filehandler instead of initializing 
    # the full FileHandler class which requires more inputs etc
    # Could technically also use Filehandler.__new__(FileHandler) but this is cleaner
    getter.filehandler = SimpleNamespace(
        # Only data attribute needed for DataGetter.get
        data={
            "file": {
                "path_downloaded": tmp_path / "file.bin",
                "url": "http://example.com/file",
            }
        }
    )

    # Create mock objects
    progress = MagicMock() # needed for get method but doesn't invoke real progress
    mock_response = MagicMock()

    # Define the mock return values
    mock_response.__enter__.return_value = mock_response
    mock_response.__exit__.return_value = False
    mock_response.iter_content.return_value = [b"data"] # Simulate content chunks
    mock_response.raise_for_status.return_value = None  # Used in download to check for HTTP errors

    # Mock the requests.get method to return the mock_response
    mock_get = MagicMock(return_value=mock_response)
    monkeypatch.setattr("dds_cli.data_getter.requests.get", mock_get)

    # Call the DataGetter.get method
    # __wrapped__ is used to call the original method without any decorators
    DataGetter.get.__wrapped__(getter, file="file", progress=progress, task=1)

    # Verify that requests.get was called with the correct timeout values
    mock_get.assert_called_once_with(
        "http://example.com/file",
        stream=True,
        timeout=(constants.CONNECT_TIMEOUT, constants.READ_TIMEOUT),
    )