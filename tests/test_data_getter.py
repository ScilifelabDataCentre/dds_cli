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
        data={
            file_name: {
                "path_downloaded": pathlib.Path(download_path or file_name),
                "url": "https://example.com/file",
                "name_in_db": file_name,
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

    # Disable retries so a single failure returns immediately
    monkeypatch.setattr(constants, "DOWNLOAD_MAX_RETRIES", 1)

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

    # Disable retries so a single failure returns immediately
    monkeypatch.setattr(constants, "DOWNLOAD_MAX_RETRIES", 1)

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


def test_get_retries_on_connection_error(monkeypatch, tmp_path):
    """Test that a transient ConnectionError is retried and succeeds."""
    file_name = "file.bin"
    file_path = tmp_path / file_name
    getter = _prepare_data_getter(file_name=file_name, download_path=file_path)

    monkeypatch.setattr(constants, "DOWNLOAD_MAX_RETRIES", 3)
    monkeypatch.setattr(constants, "DOWNLOAD_INITIAL_WAIT", 0)

    mock_response = MagicMock()
    mock_response.__enter__.return_value = mock_response
    mock_response.__exit__.return_value = False
    mock_response.iter_content.return_value = [b"data"]
    mock_response.raise_for_status.return_value = None

    call_count = 0

    def fake_get(*_, **__):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise requests.exceptions.ConnectionError("connection reset")
        return mock_response

    monkeypatch.setattr("dds_cli.data_getter.requests.get", fake_get)

    downloaded, message = DataGetter.get.__wrapped__(
        getter, file=file_name, progress=MagicMock(), task=1
    )

    assert downloaded is True
    assert message == ""
    assert call_count == 2


def test_get_fails_after_max_retries(monkeypatch):
    """Test that download fails after exhausting all retry attempts."""
    file_name = "file.txt"
    getter = _prepare_data_getter(file_name)

    monkeypatch.setattr(constants, "DOWNLOAD_MAX_RETRIES", 3)
    monkeypatch.setattr(constants, "DOWNLOAD_INITIAL_WAIT", 0)

    err = requests.exceptions.ConnectionError("connection reset")
    monkeypatch.setattr(requests, "get", lambda *_, **__: (_ for _ in ()).throw(err))

    downloaded, message = DataGetter.get.__wrapped__(
        getter, file=file_name, progress=MagicMock(), task=None
    )

    assert downloaded is False
    assert "Final error:" in message
    assert "attempt 1/3" in message
    assert "attempt 2/3" in message


def test_get_no_retry_on_404(monkeypatch):
    """Test that a 404 HTTPError breaks immediately without retrying."""
    file_name = "file.txt"
    getter = _prepare_data_getter(file_name)

    monkeypatch.setattr(constants, "DOWNLOAD_MAX_RETRIES", 5)

    mock_response = MagicMock()
    mock_response.status_code = 404
    err = requests.exceptions.HTTPError(response=mock_response)

    call_count = 0

    def fake_get(*_, **__):
        nonlocal call_count
        call_count += 1
        raise err

    monkeypatch.setattr(requests, "get", fake_get)

    downloaded, message = DataGetter.get.__wrapped__(
        getter, file=file_name, progress=MagicMock(), task=None
    )

    assert downloaded is False
    assert message == "File not found! Please contact support."
    assert call_count == 1


def test_get_retries_on_http_500(monkeypatch, tmp_path):
    """Test that a 500 HTTPError is retried."""
    file_name = "file.bin"
    file_path = tmp_path / file_name
    getter = _prepare_data_getter(file_name=file_name, download_path=file_path)

    monkeypatch.setattr(constants, "DOWNLOAD_MAX_RETRIES", 3)
    monkeypatch.setattr(constants, "DOWNLOAD_INITIAL_WAIT", 0)

    mock_500_response = MagicMock()
    mock_500_response.status_code = 500

    mock_ok_response = MagicMock()
    mock_ok_response.__enter__.return_value = mock_ok_response
    mock_ok_response.__exit__.return_value = False
    mock_ok_response.iter_content.return_value = [b"data"]
    mock_ok_response.raise_for_status.return_value = None

    call_count = 0

    def fake_get(*_, **__):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise requests.exceptions.HTTPError(response=mock_500_response)
        return mock_ok_response

    monkeypatch.setattr("dds_cli.data_getter.requests.get", fake_get)

    downloaded, message = DataGetter.get.__wrapped__(
        getter, file=file_name, progress=MagicMock(), task=1
    )

    assert downloaded is True
    assert call_count == 2


def test_get_retry_uses_exponential_backoff(monkeypatch):
    """Test that retry wait times increase exponentially."""
    file_name = "file.txt"
    getter = _prepare_data_getter(file_name)

    monkeypatch.setattr(constants, "DOWNLOAD_MAX_RETRIES", 4)
    monkeypatch.setattr(constants, "DOWNLOAD_INITIAL_WAIT", 1)
    monkeypatch.setattr(constants, "DOWNLOAD_BACKOFF_FACTOR", 2)

    err = requests.exceptions.ConnectionError("reset")
    monkeypatch.setattr(requests, "get", lambda *_, **__: (_ for _ in ()).throw(err))

    sleep_calls = []
    monkeypatch.setattr("dds_cli.data_getter.time.sleep", lambda s: sleep_calls.append(s))

    DataGetter.get.__wrapped__(
        getter, file=file_name, progress=MagicMock(), task=None
    )

    assert sleep_calls == [1, 2, 4]


def test_get_progress_reset_only_on_retry(monkeypatch, tmp_path):
    """Test that progress.reset is called on retries but not on the first attempt."""
    file_name = "file.bin"
    file_path = tmp_path / file_name
    getter = _prepare_data_getter(file_name=file_name, download_path=file_path)

    monkeypatch.setattr(constants, "DOWNLOAD_MAX_RETRIES", 3)
    monkeypatch.setattr(constants, "DOWNLOAD_INITIAL_WAIT", 0)

    mock_response = MagicMock()
    mock_response.__enter__.return_value = mock_response
    mock_response.__exit__.return_value = False
    mock_response.iter_content.return_value = [b"data"]
    mock_response.raise_for_status.return_value = None

    call_count = 0

    def fake_get(*_, **__):
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            raise requests.exceptions.ConnectionError("reset")
        return mock_response

    monkeypatch.setattr("dds_cli.data_getter.requests.get", fake_get)

    progress = MagicMock()
    task = 1

    DataGetter.get.__wrapped__(
        getter, file=file_name, progress=progress, task=task
    )

    assert progress.reset.call_count == 2
