"""Tests for retrying API requests on 502/503 (update_db, add_file_db)."""

# IMPORTS ######################################################################

import pathlib
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import dds_cli.exceptions
import dds_cli.utils
from dds_cli import constants
from dds_cli.data_getter import DataGetter
from dds_cli.data_putter import DataPutter

# HELPERS ######################################################################


def _prepare_data_getter(file_name):
    """DataGetter with one file, without running __init__."""
    getter = DataGetter.__new__(DataGetter)
    getter.filehandler = SimpleNamespace(
        data={file_name: {"name_in_db": file_name, "path_downloaded": pathlib.Path(file_name)}}
    )
    return getter


def _api_response(status_code, json_body=None):
    """Mock API response. Without json_body, .json() fails like the 11-byte 'Bad Gateway'."""
    import simplejson

    response = MagicMock()
    response.status_code = status_code
    response.ok = status_code < 400
    response.reason = "Bad Gateway" if status_code == 502 else "OK"
    if json_body is None:
        response.json.side_effect = simplejson.JSONDecodeError("Expecting value", "Bad Gateway", 0)
    else:
        response.json.return_value = json_body
    return response


def _update_db_getter():
    getter = _prepare_data_getter("file.bin")
    getter.project = "proj00001"
    getter.token = {"Authorization": "Bearer x"}
    getter.stop_doing = False
    getter.service_unavailable = None
    return getter


# TESTS ########################################################################


@pytest.fixture(autouse=True)
def file_match_empty(monkeypatch):
    """GET file/match (used after a failed POST file/new): no files in the database."""
    mock_get = MagicMock(return_value=_api_response(200, {"files": None}))
    monkeypatch.setattr("dds_cli.utils.requests.get", mock_get)
    return mock_get


def test_update_db_retries_once_on_502(monkeypatch):
    """A 502 from the proxy is retried once, and the second try succeeds."""
    monkeypatch.setattr(constants, "API_RETRY_WAIT", 0)
    responses = iter([_api_response(502), _api_response(200, {"message": "File info updated."})])
    mock_put = MagicMock(side_effect=lambda **_: next(responses))
    monkeypatch.setattr("dds_cli.utils.requests.put", mock_put)

    updated, message = DataGetter.update_db.__wrapped__(_update_db_getter(), file="file.bin")

    assert (updated, message) == (True, "File info updated.")
    assert mock_put.call_count == 2


def test_update_db_502_does_not_raise(monkeypatch):
    """Two 502s in a row: report the failure, but never stop the whole download."""
    monkeypatch.setattr(constants, "API_RETRY_WAIT", 0)
    mock_put = MagicMock(side_effect=lambda **_: _api_response(502))
    monkeypatch.setattr("dds_cli.utils.requests.put", mock_put)

    updated, message = DataGetter.update_db.__wrapped__(_update_db_getter(), file="file.bin")

    assert updated is False
    assert "502" in message
    assert mock_put.call_count == 2


def test_update_db_no_retry_on_500(monkeypatch):
    """A 500 comes from the backend itself, so it is not retried (but still caught)."""
    monkeypatch.setattr(constants, "API_RETRY_WAIT", 0)
    mock_put = MagicMock(side_effect=lambda **_: _api_response(500, {"message": "Something broke"}))
    monkeypatch.setattr("dds_cli.utils.requests.put", mock_put)

    updated, message = DataGetter.update_db.__wrapped__(_update_db_getter(), file="file.bin")

    assert updated is False
    assert "Something broke" in message
    assert mock_put.call_count == 1


def _putter_with_one_file():
    import threading
    from types import SimpleNamespace

    putter = DataPutter.__new__(DataPutter)
    putter.project = "proj00001"
    putter.token = {"Authorization": "Bearer x"}
    putter._db_add_lock = threading.Lock()
    putter.any_successful_db_add = False
    putter.stop_doing = False
    putter.service_unavailable = None
    putter.filehandler = SimpleNamespace(
        data={
            "file.txt": {
                "path_remote": "bucketname",
                "subpath": ".",
                "size_raw": 4,
                "size_processed": 40,
                "compressed": False,
                "salt": "salt",
                "public_key": "key",
                "checksum": "abc",
                "overwrite": False,
                "path_raw": "file.txt",
            }
        }
    )
    return putter


def test_add_file_db_retries_once_on_502(monkeypatch):
    """POST /file/new that gets a 502 is sent once more right away."""
    monkeypatch.setattr(constants, "API_RETRY_WAIT", 0)
    responses = iter([_api_response(502), _api_response(200, {"message": "File added"})])
    mock_post = MagicMock(side_effect=lambda **_: next(responses))
    monkeypatch.setattr("dds_cli.utils.requests.post", mock_post)

    putter = _putter_with_one_file()
    added, _ = DataPutter.add_file_db.__wrapped__(putter, file="file.txt")

    assert added is True
    assert putter.any_successful_db_add is True
    assert mock_post.call_count == 2


def test_add_file_db_gives_up_after_second_502(monkeypatch):
    """Two 502s: return False, so the file is handled by retry_add_file_db at the end."""
    monkeypatch.setattr(constants, "API_RETRY_WAIT", 0)
    mock_post = MagicMock(side_effect=lambda **_: _api_response(502))
    monkeypatch.setattr("dds_cli.utils.requests.post", mock_post)

    added, message = DataPutter.add_file_db.__wrapped__(_putter_with_one_file(), file="file.txt")

    assert added is False
    assert "502" in message
    assert mock_post.call_count == 2


def test_add_file_db_no_retry_on_400(monkeypatch):
    """A 400 (e.g. file already exists) is not a proxy error and is not retried."""
    mock_post = MagicMock(
        side_effect=lambda **_: _api_response(400, {"message": "File already exists"})
    )
    monkeypatch.setattr("dds_cli.utils.requests.post", mock_post)

    added, _ = DataPutter.add_file_db.__wrapped__(_putter_with_one_file(), file="file.txt")

    assert added is False
    assert mock_post.call_count == 1


def test_perform_request_with_retry_gives_up_after_retries(monkeypatch):
    """The last error is raised when all attempts fail."""
    monkeypatch.setattr(constants, "API_RETRY_WAIT", 0)
    err = dds_cli.exceptions.NonJsonResponseError("Bad Gateway", status_code=502)
    mock_request = MagicMock(side_effect=err)
    monkeypatch.setattr(dds_cli.utils, "perform_request", mock_request)

    with pytest.raises(dds_cli.exceptions.ApiResponseError):
        dds_cli.utils.perform_request_with_retry("url", method="put", retries=2)

    assert mock_request.call_count == 3


def test_perform_request_with_retry_no_retry_on_request_error(monkeypatch):
    """A connection error is not retried here (the request may have reached the backend)."""
    err = dds_cli.exceptions.ApiRequestError("timeout")
    mock_request = MagicMock(side_effect=err)
    monkeypatch.setattr(dds_cli.utils, "perform_request", mock_request)

    with pytest.raises(dds_cli.exceptions.ApiRequestError):
        dds_cli.utils.perform_request_with_retry("url", method="post")

    assert mock_request.call_count == 1


# MAINTENANCE (503 FROM THE DDS BACKEND) #######################################

MAINTENANCE = {"message": "Maintenance of DDS is ongoing."}


def test_perform_request_backend_503_is_service_unavailable(monkeypatch):
    """A 503 with a JSON body comes from dds_web (maintenance) -> ServiceUnavailableError."""
    monkeypatch.setattr(
        "dds_cli.utils.requests.put", MagicMock(return_value=_api_response(503, MAINTENANCE))
    )

    with pytest.raises(dds_cli.exceptions.ServiceUnavailableError, match="Maintenance") as err:
        dds_cli.utils.perform_request("url", method="put")

    # Still a DDSCLIException, so existing callers behave as before.
    assert isinstance(err.value, dds_cli.exceptions.DDSCLIException)
    assert err.value.status_code == 503


def test_retry_skips_backend_503(monkeypatch):
    """Maintenance is not retried."""
    mock_put = MagicMock(return_value=_api_response(503, MAINTENANCE))
    monkeypatch.setattr("dds_cli.utils.requests.put", mock_put)

    with pytest.raises(dds_cli.exceptions.ServiceUnavailableError):
        dds_cli.utils.perform_request_with_retry("url", method="put")

    assert mock_put.call_count == 1


def test_retry_proxy_503(monkeypatch):
    """A 503 without a JSON body comes from the proxy and is retried once."""
    monkeypatch.setattr(constants, "API_RETRY_WAIT", 0)
    responses = iter([_api_response(503), _api_response(200, {"message": "ok"})])
    mock_put = MagicMock(side_effect=lambda **_: next(responses))
    monkeypatch.setattr("dds_cli.utils.requests.put", mock_put)

    response_json, _ = dds_cli.utils.perform_request_with_retry("url", method="put")

    assert response_json == {"message": "ok"}
    assert mock_put.call_count == 2


def test_update_db_stops_download_on_maintenance(monkeypatch):
    """update_db on maintenance: no retry, returns failure and stops the files not started."""
    mock_put = MagicMock(return_value=_api_response(503, MAINTENANCE))
    monkeypatch.setattr("dds_cli.utils.requests.put", mock_put)

    getter = _update_db_getter()
    updated, message = DataGetter.update_db.__wrapped__(getter, file="file.bin")

    assert updated is False
    assert "Maintenance" in message
    assert mock_put.call_count == 1
    assert getter.stop_doing is True
    assert isinstance(getter.service_unavailable, dds_cli.exceptions.ServiceUnavailableError)


def test_add_file_db_stops_upload_on_maintenance(monkeypatch):
    """add_file_db on maintenance: no retry, returns failure and stops the files not started."""
    mock_post = MagicMock(return_value=_api_response(503, MAINTENANCE))
    monkeypatch.setattr("dds_cli.utils.requests.post", mock_post)

    putter = _putter_with_one_file()
    added, message = DataPutter.add_file_db.__wrapped__(putter, file="file.txt")

    assert added is False
    assert "Maintenance" in message
    assert mock_post.call_count == 1
    assert putter.any_successful_db_add is False
    assert putter.stop_doing is True
    assert isinstance(putter.service_unavailable, dds_cli.exceptions.ServiceUnavailableError)


def test_add_file_db_maintenance_marks_failed_op(monkeypatch):
    """The file is in the bucket: it must get failed_op 'add_file_db', so it is saved in the
    failed delivery log and 'retry_add_file_db' can add it later."""
    monkeypatch.setattr(
        "dds_cli.utils.requests.post", MagicMock(return_value=_api_response(503, MAINTENANCE))
    )
    putter = _putter_with_one_file()
    putter.status = {"file.txt": {"add_file_db": {"started": False, "done": False}}}

    added, _ = DataPutter.add_file_db(putter, file="file.txt")  # with @update_status

    assert added is False
    assert putter.status["file.txt"]["failed_op"] == "add_file_db"


def test_verify_proceed_cancels_new_files_on_maintenance(caplog):
    """After maintenance is seen, files not started yet are not started."""
    from dds_cli.custom_decorators import verify_proceed

    called = MagicMock(return_value=(True, ""))

    @verify_proceed
    def work(self, file):
        return called(file)

    putter = _putter_with_one_file()
    putter.stop_for_maintenance(dds_cli.exceptions.ServiceUnavailableError("Maintenance"))

    assert work(putter, "file.txt") is False
    called.assert_not_called()
    assert "Service unavailable - cancelling file" in caplog.text


@pytest.mark.parametrize("already_cancelled", [False, True])
def test_verify_proceed_cancels_download_file_with_path_key(caplog, already_cancelled):
    """Download file keys are pathlib.Path objects: the cancel message must not crash."""
    from dds_cli.custom_decorators import verify_proceed

    called = MagicMock(return_value=(True, ""))

    @verify_proceed
    def work(self, file):
        return called(file)

    getter = _update_db_getter()
    file = pathlib.Path("dir/file.bin")
    getter.status = {file: {"cancel": already_cancelled, "started": False}}
    if not already_cancelled:
        getter.stop_for_maintenance(dds_cli.exceptions.ServiceUnavailableError("Maintenance"))

    assert work(getter, file) is False
    called.assert_not_called()
    assert str(file) in caplog.text  # dir\file.bin on Windows


def test_stop_for_maintenance_log_has_no_double_period(caplog):
    """The API message ends with a period; the log line must not get two."""
    putter = _putter_with_one_file()
    putter.stop_for_maintenance(
        dds_cli.exceptions.ServiceUnavailableError("Maintenance of DDS is ongoing.")
    )

    assert "Maintenance of DDS is ongoing. Stopping:" in caplog.text
    assert ".." not in caplog.text


def test_stop_for_maintenance_keeps_first_error_and_raises_later():
    """The error is raised once, from the main thread, after the workers are done."""
    putter = _putter_with_one_file()
    putter.raise_if_service_unavailable()  # nothing saved: no error

    first = dds_cli.exceptions.ServiceUnavailableError("first")
    putter.stop_for_maintenance(first)
    putter.stop_for_maintenance(dds_cli.exceptions.ServiceUnavailableError("second"))

    with pytest.raises(dds_cli.exceptions.ServiceUnavailableError) as err:
        putter.raise_if_service_unavailable()
    assert err.value is first


# IN-FLIGHT FILES ON MAINTENANCE ###############################################


def _download_response(chunks):
    response = MagicMock()
    response.__enter__.return_value = response
    response.__exit__.return_value = False
    response.iter_content.return_value = chunks
    response.raise_for_status.return_value = None
    response.headers.get.return_value = 8
    return response


def _getter_for_download(tmp_path):
    getter = _update_db_getter()
    getter.filehandler.data["file.bin"].update(
        {"path_downloaded": tmp_path / "file.bin", "url": "https://example.com/f", "size_stored": 8}
    )
    return getter


def test_get_stops_running_download_on_maintenance(monkeypatch, tmp_path, caplog):
    """Maintenance seen by another thread stops a running download at the next chunk."""
    getter = _getter_for_download(tmp_path)

    def chunks():
        yield b"data"
        getter.stop_for_maintenance(dds_cli.exceptions.ServiceUnavailableError("Maintenance"))
        yield b"more"

    mock_get = MagicMock(return_value=_download_response(chunks()))
    monkeypatch.setattr("dds_cli.data_getter.requests.get", mock_get)

    downloaded, message = DataGetter.get.__wrapped__(
        getter, file="file.bin", progress=MagicMock(), task=1
    )

    assert downloaded is False
    assert "Service unavailable" in message
    assert mock_get.call_count == 1  # no retry
    assert not (tmp_path / "file.bin").exists()  # partial file removed
    assert "could not be completed" not in caplog.text  # no network advice


def test_get_not_started_on_maintenance(monkeypatch, tmp_path):
    """No GET is sent once maintenance is known."""
    getter = _getter_for_download(tmp_path)
    getter.stop_for_maintenance(dds_cli.exceptions.ServiceUnavailableError("Maintenance"))
    mock_get = MagicMock()
    monkeypatch.setattr("dds_cli.data_getter.requests.get", mock_get)

    downloaded, message = DataGetter.get.__wrapped__(
        getter, file="file.bin", progress=MagicMock(), task=1
    )

    assert downloaded is False
    assert "Service unavailable" in message
    mock_get.assert_not_called()


def test_upload_skips_s3_put_on_maintenance(monkeypatch, tmp_path):
    """A file encrypted after maintenance is known is not uploaded (no orphan object)."""
    processed = tmp_path / "file.txt.ccp"
    processed.write_bytes(b"encrypted")

    putter = _putter_with_one_file()
    putter.filehandler.data["file.txt"]["path_processed"] = processed
    putter.filehandler.stream_from_file = MagicMock()
    putter.keys = None
    putter.silent = True
    putter.method = "put"
    putter.status = {"file.txt": {}}
    putter.put = MagicMock()
    putter.add_file_db = MagicMock()

    encryptor = MagicMock()
    encryptor.encrypt_filechunks.return_value = (True, "")
    encryptor_cm = MagicMock()
    encryptor_cm.__enter__.return_value = encryptor
    monkeypatch.setattr("dds_cli.data_putter.fe.Encryptor", MagicMock(return_value=encryptor_cm))

    putter.stop_for_maintenance(dds_cli.exceptions.ServiceUnavailableError("Maintenance"))
    # Skip @verify_proceed (stop_doing would cancel before encryption) and @subpath_required
    ok, message = DataPutter.protect_and_upload.__wrapped__.__wrapped__(
        putter, file="file.txt", progress=MagicMock()
    )

    assert ok is False
    assert "Service unavailable" in message
    putter.put.assert_not_called()
    putter.add_file_db.assert_not_called()
    assert putter.status["file.txt"]["failed_op"] == "put"
    assert not processed.exists()


# POST REACHED THE BACKEND BUT THE CLIENT GOT A 502 ############################

FILE_EXISTS_500 = {"message": "Internal Server Error"}  # FileExistsError is not handled


def test_add_file_db_502_then_exists_is_added(monkeypatch, file_match_empty):
    """First POST added the row but the client got a 502; the retry fails because the
    file exists. file/match shows our name_in_bucket, so the file is added."""
    monkeypatch.setattr(constants, "API_RETRY_WAIT", 0)
    responses = iter([_api_response(502), _api_response(500, FILE_EXISTS_500)])
    mock_post = MagicMock(side_effect=lambda **_: next(responses))
    monkeypatch.setattr("dds_cli.utils.requests.post", mock_post)
    file_match_empty.return_value = _api_response(200, {"files": {"file.txt": "bucketname"}})

    putter = _putter_with_one_file()
    added, _ = DataPutter.add_file_db.__wrapped__(putter, file="file.txt")

    assert added is True
    assert putter.any_successful_db_add is True
    assert mock_post.call_count == 2
    assert file_match_empty.call_args.kwargs["json"] == ["file.txt"]


def test_add_file_db_exists_with_other_name_in_bucket_fails(monkeypatch, file_match_empty):
    """The file is in the database, but from another upload: still a failure."""
    monkeypatch.setattr(
        "dds_cli.utils.requests.post",
        MagicMock(return_value=_api_response(500, FILE_EXISTS_500)),
    )
    file_match_empty.return_value = _api_response(200, {"files": {"file.txt": "other"}})

    putter = _putter_with_one_file()
    added, _ = DataPutter.add_file_db.__wrapped__(putter, file="file.txt")

    assert added is False
    assert putter.any_successful_db_add is False


def test_add_file_db_match_check_fails(monkeypatch, file_match_empty):
    """If file/match fails too, the file stays failed with the original error."""
    monkeypatch.setattr(
        "dds_cli.utils.requests.post",
        MagicMock(return_value=_api_response(500, FILE_EXISTS_500)),
    )
    file_match_empty.return_value = _api_response(502)

    added, message = DataPutter.add_file_db.__wrapped__(_putter_with_one_file(), file="file.txt")

    assert added is False
    assert "Internal Server Error" in message


def test_add_file_db_put_is_not_checked(monkeypatch, file_match_empty):
    """Overwrite (PUT): the file was in the database before, so file/match tells nothing."""
    monkeypatch.setattr(
        "dds_cli.utils.requests.put",
        MagicMock(return_value=_api_response(500, FILE_EXISTS_500)),
    )
    putter = _putter_with_one_file()
    putter.filehandler.data["file.txt"]["overwrite"] = True

    added, _ = DataPutter.add_file_db.__wrapped__(putter, file="file.txt")

    assert added is False
    file_match_empty.assert_not_called()


# THE RETRY NEEDS BOTH: NO JSON BODY AND 502/503 ###############################


def test_no_json_body_is_non_json_response_error(monkeypatch):
    """An answer without a JSON body is NonJsonResponseError (still an ApiResponseError)."""
    monkeypatch.setattr("dds_cli.utils.requests.put", MagicMock(return_value=_api_response(502)))
    with pytest.raises(dds_cli.exceptions.NonJsonResponseError) as err:
        dds_cli.utils.perform_request("https://x/file/update", method="put", headers={})
    assert isinstance(err.value, dds_cli.exceptions.ApiResponseError)
    assert err.value.status_code == 502


def test_retry_skips_json_502(monkeypatch):
    """A 502 WITH a JSON body comes from the DDS API: not retried."""
    monkeypatch.setattr(constants, "API_RETRY_WAIT", 0)
    mock_put = MagicMock(return_value=_api_response(502, {"message": "from the API"}))
    monkeypatch.setattr("dds_cli.utils.requests.put", mock_put)

    with pytest.raises(dds_cli.exceptions.DDSCLIException):
        dds_cli.utils.perform_request_with_retry("https://x/file/update", method="put", headers={})
    assert mock_put.call_count == 1


def test_retry_skips_api_response_error_with_502_status(monkeypatch):
    """Only NonJsonResponseError is retried, not any ApiResponseError with status 502."""
    monkeypatch.setattr(constants, "API_RETRY_WAIT", 0)
    err = dds_cli.exceptions.ApiResponseError("JSON error", status_code=502)
    mock_request = MagicMock(side_effect=err)
    monkeypatch.setattr("dds_cli.utils.perform_request", mock_request)

    with pytest.raises(dds_cli.exceptions.ApiResponseError):
        dds_cli.utils.perform_request_with_retry("https://x", method="put", headers={})
    assert mock_request.call_count == 1


# END OF UPLOAD BATCH ##########################################################


def _run_put_with(monkeypatch, putter):
    """Run data_putter.put() with a mocked DataPutter and no files to upload."""
    import dds_cli.data_putter

    putter_cm = MagicMock()
    putter_cm.__enter__.return_value = putter
    putter_cm.__exit__.return_value = False
    monkeypatch.setattr(dds_cli.data_putter, "DataPutter", MagicMock(return_value=putter_cm))
    monkeypatch.setattr(dds_cli.data_putter, "Progress", MagicMock())
    dds_cli.data_putter.put(
        project="proj00001",
        source=(),
        source_path_file=None,
        break_on_fail=False,
        overwrite=False,
        num_threads=1,
        silent=True,
        no_prompt=True,
        token_path=None,
        destination=None,
        staging_dir=None,
    )


def _batch_putter(service_unavailable):
    putter = MagicMock()
    putter.filehandler.data = {}
    putter.failed_delivery_log.is_file.return_value = True
    putter.service_unavailable = service_unavailable
    putter.raise_if_service_unavailable.side_effect = (
        service_unavailable if service_unavailable else None
    )
    return putter


def test_put_skips_db_retry_on_maintenance(monkeypatch):
    """Known maintenance: no retry_add_file_db and no timestamp refresh, just the error."""
    putter = _batch_putter(dds_cli.exceptions.ServiceUnavailableError("Maintenance"))

    with pytest.raises(dds_cli.exceptions.ServiceUnavailableError):
        _run_put_with(monkeypatch, putter)

    putter.retry_add_file_db.assert_not_called()
    putter.touch_project_after_upload.assert_not_called()


def test_put_runs_db_retry_without_maintenance(monkeypatch):
    """No maintenance: the end-of-batch retry and timestamp refresh run as before."""
    putter = _batch_putter(None)

    _run_put_with(monkeypatch, putter)

    putter.retry_add_file_db.assert_called_once()
    putter.touch_project_after_upload.assert_called_once()
