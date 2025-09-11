"""Tests for the data_getter module."""

# IMPORTS ######################################################################


import pathlib
import requests
from types import SimpleNamespace
from unittest.mock import MagicMock

from dds_cli.data_getter import DataGetter
from dds_cli import constants


# HELPERS ######################################################################


def _prepare_data_getter(file_name, download_path=None):
    """Mock a DataGetter instance with a filehandler containing a single file entry."""
    # Create DataGetter instance without running __init__
    dg = DataGetter.__new__(DataGetter)

    # Mock filehandler with necessary data
    # Using SimpleNamespace because it allows you to create simple objects
    # with attributes without defining a custom class
    # Here we use it to mock the filehandler instead of initializing
    # the full FileHandler class which requires more inputs etc
    # Could technically also use Filehandler.__new__(FileHandler) but this is cleaner
    dg.filehandler = SimpleNamespace(
        # Only data attribute needed for DataGetter.get
        data={
            file_name: {
                "path_downloaded": pathlib.Path(download_path or file_name),
                "url": "https://example.com/file",
            }
        }
    )
    return dg


# TESTS ########################################################################


def test_get_uses_timeout(monkeypatch, tmp_path):
    """Test that DataGetter.get uses the correct timeout values.

    monkeypatch is a pytest fixture that allows you to modify objects temporatily.
    tmp_path is a pytest fixture that provides a temporary directory.
    """
    file_name = "file.bin"
    file_path = tmp_path / file_name

    # Mock DataGetter instance with helper
    getter = _prepare_data_getter(file_name=file_name, download_path=file_path)

    # Create mock objects
    progress = MagicMock()  # needed for get method but doesn't invoke real progress
    mock_response = MagicMock()

    # Define the mock return values
    mock_response.__enter__.return_value = mock_response
    mock_response.__exit__.return_value = False
    mock_response.iter_content.return_value = [b"data"]  # Simulate content chunks
    mock_response.raise_for_status.return_value = None  # Used in download to check for HTTP errors

    # Mock the requests.get method to return the mock_response
    mock_get = MagicMock(return_value=mock_response)
    monkeypatch.setattr("dds_cli.data_getter.requests.get", mock_get)

    # Call the DataGetter.get method
    # __wrapped__ is used to call the original method without any decorators
    DataGetter.get.__wrapped__(getter, file="file.bin", progress=progress, task=1)

    # Verify that requests.get was called with the correct timeout values
    mock_get.assert_called_once_with(
        "https://example.com/file",
        stream=True,
        timeout=(constants.CONNECT_TIMEOUT, constants.READ_TIMEOUT),
    )


def test_get_connect_timeout(monkeypatch):
    """Test that DataGetter.get handles a connection timeout correctly."""
    file_name = "file.txt"

    # Mock DataGetter instance with helper
    getter = _prepare_data_getter(file_name)

    err = requests.exceptions.ConnectTimeout("connect timeout")

    # Helper function to replace requests.get and raise a timeout error
    def fake_get(*_, **__):
        raise err

    # Use monkeypatch to replace requests.get with our fake_get function
    monkeypatch.setattr(requests, "get", fake_get)

    # Call the DataGetter.get method
    # __wrapped__ is used to call the original method without any decorators
    downloaded, message = DataGetter.get.__wrapped__(
        getter, file=file_name, progress=None, task=None
    )

    # Verify that the method returns the expected values
    assert (downloaded, message) == (False, str(err))
    assert not pathlib.Path(file_name).exists()


def test_get_read_timeout(monkeypatch):
    """Test that DataGetter.get handles a read timeout correctly."""
    file_name = "file.txt"

    # Mock DataGetter instance with helper
    getter = _prepare_data_getter(file_name)

    err = requests.exceptions.ReadTimeout("read timeout")

    # Helper function to replace requests.get and raise a timeout error
    def fake_get(*_, **__):
        raise err

    # Use monkeypatch to replace requests.get with our fake_get function
    monkeypatch.setattr(requests, "get", fake_get)

    # Call the DataGetter.get method
    # __wrapped__ is used to call the original method without any decorators
    downloaded, message = DataGetter.get.__wrapped__(
        getter, file=file_name, progress=None, task=None
    )

    # Verify that the method returns the expected values
    assert (downloaded, message) == (False, str(err))
    assert not pathlib.Path(file_name).exists()
