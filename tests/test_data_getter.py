"""Tests for the data_getter module."""

# IMPORTS ######################################################################

import logging
import pathlib
import pytest
import requests
from types import SimpleNamespace
from unittest.mock import MagicMock

from dds_cli.data_getter import DataGetter
from dds_cli import constants


# HELPERS ######################################################################


def _prepare_data_getter(file_name, download_path=None, size_stored=4):
    """Mock a DataGetter instance with a filehandler containing a single file entry.

    `size_stored` defaults to 4 to match the canonical ``b"data"`` body used by most
    tests below; the byte-count check inside ``get()`` only passes when the on-disk
    size equals this value.
    """
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
                "size_stored": size_stored,
            }
        }
    )
    return dg


def _ok_response(body=b"data"):
    """Build a mock requests.Response that streams ``body`` as a single chunk.

    Sets a Content-Length header matching the body length so the truncation
    check inside ``get()`` is satisfied. Tests that want to simulate a
    truncated response should override ``headers.get`` themselves.
    """
    mock_response = MagicMock()
    mock_response.__enter__.return_value = mock_response
    mock_response.__exit__.return_value = False
    mock_response.iter_content.return_value = [body]
    mock_response.raise_for_status.return_value = None
    mock_response.headers.get.return_value = len(body)
    return mock_response


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
    mock_response = _ok_response()

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

    mock_response = _ok_response()

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

    mock_ok_response = _ok_response()

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

    DataGetter.get.__wrapped__(getter, file=file_name, progress=MagicMock(), task=None)

    assert sleep_calls == [1, 2, 4]


def test_get_progress_reset_only_on_retry(monkeypatch, tmp_path):
    """Test that progress.reset is called on retries but not on the first attempt."""
    file_name = "file.bin"
    file_path = tmp_path / file_name
    getter = _prepare_data_getter(file_name=file_name, download_path=file_path)

    monkeypatch.setattr(constants, "DOWNLOAD_MAX_RETRIES", 3)
    monkeypatch.setattr(constants, "DOWNLOAD_INITIAL_WAIT", 0)

    mock_response = _ok_response()

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

    DataGetter.get.__wrapped__(getter, file=file_name, progress=progress, task=task)

    assert progress.reset.call_count == 2


def test_get_detects_truncated_stream_via_content_length(monkeypatch, tmp_path):
    """A clean TCP close with fewer bytes than Content-Length must trigger a retry.

    Reproduces the failure mode from the May 2026 ngisthlm02415 incident:
    requests/urllib3 happily report a "successful" download even when the body
    is short, so ``get()`` has to validate the byte count itself.
    """
    file_name = "file.bin"
    file_path = tmp_path / file_name
    # Server says 100 bytes, body delivers 4 — mimics a connection drop
    # mid-stream where the FIN arrives before the full payload.
    getter = _prepare_data_getter(file_name=file_name, download_path=file_path, size_stored=100)

    monkeypatch.setattr(constants, "DOWNLOAD_MAX_RETRIES", 3)
    monkeypatch.setattr(constants, "DOWNLOAD_INITIAL_WAIT", 0)

    truncated_response = _ok_response(body=b"data")
    truncated_response.headers.get.return_value = 100  # advertised, not delivered

    monkeypatch.setattr("dds_cli.data_getter.requests.get", lambda *_, **__: truncated_response)

    downloaded, message = DataGetter.get.__wrapped__(
        getter, file=file_name, progress=MagicMock(), task=1
    )

    # The retry path engaged on every attempt and ultimately gave up.
    assert downloaded is False
    assert "Truncated download" in message
    assert "attempt 1/3" in message


def test_get_detects_size_mismatch_against_size_stored(monkeypatch, tmp_path):
    """If the body size matches Content-Length but not size_stored, still fail.

    This catches the case where a misbehaving S3-compatible backend serves a
    Content-Length that disagrees with what DDS recorded — we trust the DDS
    metadata as the source of truth.
    """
    file_name = "file.bin"
    file_path = tmp_path / file_name
    # DDS expects 100 bytes; the proxy reports and delivers 4 — they agree
    # with each other but disagree with the catalogue.
    getter = _prepare_data_getter(file_name=file_name, download_path=file_path, size_stored=100)

    monkeypatch.setattr(constants, "DOWNLOAD_MAX_RETRIES", 2)
    monkeypatch.setattr(constants, "DOWNLOAD_INITIAL_WAIT", 0)

    # Content-Length matches the 4-byte body, so the truncation guard passes;
    # the size_stored comparison is the one that has to catch this.
    consistent_short_response = _ok_response(body=b"data")  # headers.get returns 4

    monkeypatch.setattr(
        "dds_cli.data_getter.requests.get", lambda *_, **__: consistent_short_response
    )

    downloaded, message = DataGetter.get.__wrapped__(
        getter, file=file_name, progress=MagicMock(), task=1
    )

    assert downloaded is False
    assert "Size mismatch" in message


def test_get_cleans_up_partial_file_on_failure(monkeypatch, tmp_path):
    """After exhausting retries, the truncated blob must not be left on disk."""
    file_name = "file.bin"
    file_path = tmp_path / file_name
    getter = _prepare_data_getter(file_name=file_name, download_path=file_path, size_stored=100)

    monkeypatch.setattr(constants, "DOWNLOAD_MAX_RETRIES", 2)
    monkeypatch.setattr(constants, "DOWNLOAD_INITIAL_WAIT", 0)

    truncated_response = _ok_response(body=b"data")
    truncated_response.headers.get.return_value = 100

    monkeypatch.setattr("dds_cli.data_getter.requests.get", lambda *_, **__: truncated_response)

    DataGetter.get.__wrapped__(getter, file=file_name, progress=MagicMock(), task=1)

    # The point: don't leave a useless 4-byte file masquerading as a download.
    assert not file_path.exists()


def test_get_retries_on_truncation_and_eventually_succeeds(monkeypatch, tmp_path):
    """A retry after a truncated attempt should produce a complete file."""
    file_name = "file.bin"
    file_path = tmp_path / file_name
    getter = _prepare_data_getter(file_name=file_name, download_path=file_path, size_stored=4)

    monkeypatch.setattr(constants, "DOWNLOAD_MAX_RETRIES", 3)
    monkeypatch.setattr(constants, "DOWNLOAD_INITIAL_WAIT", 0)

    # First attempt: server claims 4 bytes but only delivers 2 — truncation.
    truncated = MagicMock()
    truncated.__enter__.return_value = truncated
    truncated.__exit__.return_value = False
    truncated.iter_content.return_value = [b"da"]
    truncated.raise_for_status.return_value = None
    truncated.headers.get.return_value = 4

    # Second attempt: clean 4-byte response.
    full = _ok_response(body=b"data")

    responses = iter([truncated, full])
    monkeypatch.setattr("dds_cli.data_getter.requests.get", lambda *_, **__: next(responses))

    downloaded, message = DataGetter.get.__wrapped__(
        getter, file=file_name, progress=MagicMock(), task=1
    )

    assert downloaded is True
    assert message == ""
    assert file_path.read_bytes() == b"data"


def test_get_tolerates_missing_or_malformed_content_length(monkeypatch, tmp_path):
    """Content-Length absent / chunked / garbled must not crash get().

    AWS S3 always returns a clean integer, but S3-compatible backends
    sometimes use Transfer-Encoding: chunked (no Content-Length header) or
    sit behind a proxy that rewrites headers. In those cases the
    Content-Length truncation guard is skipped and we fall back to the
    size_stored byte-count check, which still catches truncation.
    """
    file_name = "file.bin"
    file_path = tmp_path / file_name
    # body length matches size_stored, so size_stored check passes;
    # this test asserts we don't crash on the int() parse alone.
    getter = _prepare_data_getter(file_name=file_name, download_path=file_path, size_stored=4)

    monkeypatch.setattr(constants, "DOWNLOAD_MAX_RETRIES", 1)

    # Each entry is what req.headers.get("Content-Length", 0) might return
    # from a misbehaving server: missing (default 0 substituted), chunked
    # responses surface as None, and garbled values like "abc" come from
    # broken proxies that concatenate or rewrite headers.
    for header_value in (0, None, "abc", "12, 12"):
        response = _ok_response(body=b"data")
        response.headers.get.return_value = header_value

        monkeypatch.setattr("dds_cli.data_getter.requests.get", lambda *_, **__: response)

        downloaded, message = DataGetter.get.__wrapped__(
            getter, file=file_name, progress=MagicMock(), task=1
        )

        assert downloaded is True, f"failed for Content-Length={header_value!r}: {message}"


def test_get_warns_user_about_connection_on_exhausted_retries(monkeypatch, tmp_path, caplog):
    """After all retries fail, get() must emit a user-facing warning suggesting
    the user check their internet connection and sleep settings."""
    file_name = "file.bin"
    file_path = tmp_path / file_name
    getter = _prepare_data_getter(file_name=file_name, download_path=file_path, size_stored=100)

    monkeypatch.setattr(constants, "DOWNLOAD_MAX_RETRIES", 2)
    monkeypatch.setattr(constants, "DOWNLOAD_INITIAL_WAIT", 0)

    truncated_response = _ok_response(body=b"data")
    truncated_response.headers.get.return_value = 100
    monkeypatch.setattr("dds_cli.data_getter.requests.get", lambda *_, **__: truncated_response)

    with caplog.at_level(logging.WARNING, logger="dds_cli.data_getter"):
        DataGetter.get.__wrapped__(getter, file=file_name, progress=MagicMock(), task=1)

    warning_texts = " ".join(
        r.getMessage() for r in caplog.records if r.levelno == logging.WARNING
    )
    assert "internet connection" in warning_texts.lower()
    assert "sleep" in warning_texts.lower()


def test_download_and_verify_raises_on_size_contract_violation(tmp_path):
    """download_and_verify() must raise RuntimeError when get() returns True but
    the on-disk file doesn't match size_stored.

    This guards against a future get() refactor that silently breaks the size
    guarantee and would otherwise let a truncated blob reach decryption,
    reintroducing the failed_op='crypto' misattribution from the May 2026 incident.
    """
    file_name = "file.bin"
    file_path = tmp_path / file_name

    # Write a file that is the wrong size (2 bytes; size_stored expects 100).
    file_path.write_bytes(b"xx")

    getter = _prepare_data_getter(file_name=file_name, download_path=file_path, size_stored=100)
    getter.filehandler.data[file_name]["size_original"] = 80
    getter.silent = False

    # get() incorrectly claims success despite the on-disk size mismatch.
    getter.get = MagicMock(return_value=(True, ""))

    progress = MagicMock()
    progress.add_task.return_value = 1

    # Bypass @verify_proceed and @subpath_required to call the raw function directly.
    with pytest.raises(RuntimeError, match="get\\(\\) returned True but size mismatch"):
        DataGetter.download_and_verify.__wrapped__.__wrapped__(
            getter, file=file_name, progress=progress
        )
        assert message == ""
