from datetime import datetime, timedelta
from os import path
from io import StringIO
import sys
from typing import Dict, List, Tuple

from requests import get
from requests.exceptions import JSONDecodeError

from flask import Response
import rich
from rich.table import Table
import pytest

from _pytest.capture import CaptureFixture
from requests_mock.adapter import _Matcher
from requests_mock.mocker import Mocker
from pytest import raises
from _pytest.logging import LogCaptureFixture
from pyfakefs.fake_filesystem import FakeFilesystem
from unittest import mock
from unittest.mock import MagicMock

from dds_cli import DDSEndpoint
from dds_cli.exceptions import (
    ApiRequestError,
    ApiResponseError,
    DDSCLIException,
    NoDataError,
    TokenDeserializationError,
    TokenExpirationMissingError,
)
from dds_cli.utils import (
    create_table,
    delete_folder,
    format_api_response,
    get_deletion_confirmation,
    get_json_response,
    get_required_in_response,
    get_token_expiration_time,
    get_token_header_contents,
    multiple_help_text,
    perform_request,
    print_or_page,
    readable_timedelta,
    sort_items,
)

sample_fully_authenticated_token = (
    "eyJhbGciOiJBMjU2S1ciLCJlbmMiOiJBMjU2R0"
    "NNIiwiZXhwIjoiMjAyMi0wMi0yNFQxNDo1MTow"
    "Ni4yMTg3OTgifQ.Ul5rfhy0S9iaX2dPGH93HtL"
    "-3tVdGBdAzzoTQXb_QJrcIIA0wEwdQw.95ii5p"
    "anPoIUV1Mf.cAwnDuri4kxjwnQfY48pS0rZ-ob"
    "-RnKBacUcOe0l3RJrMCbc2nfkdkzc7KBH06ESi"
    "D-I7MU-U6270uLa2M4ZcLk0AkCZ3S7xrm9-bDu"
    "_73yCDCIQravwphlxCVSSrNQUPU8BonwBuDu-5"
    "WjuJyL_zC7MBcduxau8L0Hpk0IOLfIDgEtq9uR"
    "ELIxjbw1-YEhOtUBKm3E3jevmohgCt7RqcbbuB"
    "ZtZgYSm5NjOO1XhHBz_kZo1lhONNVVDNUkAoAP"
    "FoJ7WOAPajCGiDi8yyq7e-ojcxoSf0gl5NVd25"
    "cmO7i4OqsXB9VNlN5asEZE4WXAmVrQTppCbTG_"
    "9te04fCDwGabzDqtdfUqX-d_yaQ_UYHmJMN1xc"
    "4aF-uWZtk3loyMZU-uedQPqsJSZ.ay0MIzbtmt"
    "GsxUm2blaKUA"
)

token_without_exp_claim_in_header = (
    "eyJhbGciOiJBMjU2S1ciLCJlbmMiOiJBMjU2R"
    "0NNIn0.3H7fZh-rxkSuERSgknz4fOtseDn6PN"
    "c0RR-1IU8EmoTfpOuMOTvVbg.a_UwR9ArB6kn"
    "1LEB.7Ko4g1Xs9S_EQsAbGCtc96x_h3P6lwZz"
    "_X6t1EKA-EFeLXgwjAHuX5S_rC7YK28rqIT_m"
    "9FQABgTSgi0nBHCUurPA43U2P2mDR9UOvCHFY"
    "QXLKyO3M-ykVrmNwSGZMjo3HHrmcuICiwiH7l"
    "boGl5Vr-iSFpyyuy33thSrlwfutI80sKe3RSm"
    "Kup_Mh7tM0mw0WbQezfAcNR_52BeP_ncbVxFl"
    "714ikyo2HCk0bKREIpetdaKCaoZgqlhOarlAU"
    "GwPaKtdgmXb7Ef4VKfYdnLIxqzv3RtVmZiEb1"
    "L-xCS4vnwXvw_bEa_QU-5HfyLYOszjAHiYHxr"
    "q8v1xnfoyWfd20OxQMhYueVzlPw1HfMSfvCNV"
    "LZO-vNNKHTaGnPyGuykhMNScIgkR1l8.TEp4L"
    "s4c29JtGogmdYbTbw"
)

# sort_items


def test_sort_items_empty_list() -> None:
    assert sort_items(items=[], sort_by="") == []


def test_sort_items_sorted() -> None:
    assert sort_items(
        items=[{"column": 1}, {"column": 2}, {"column": 3}, {"column": 4}, {"column": 5}],
        sort_by="column",
    ) == [{"column": 1}, {"column": 2}, {"column": 3}, {"column": 4}, {"column": 5}]


def test_sort_items_unsorted() -> None:
    assert sort_items(
        items=[{"column": 5}, {"column": 4}, {"column": 3}, {"column": 2}, {"column": 1}],
        sort_by="column",
    ) == [{"column": 1}, {"column": 2}, {"column": 3}, {"column": 4}, {"column": 5}]


# create_table


def test_create_table() -> None:
    columns: List = ["column"]
    rows: Dict[str] = [{}]
    rows[0]["column"] = 0
    table: Table = create_table("", columns, rows)

    assert len(table.columns) == 1
    assert table.row_count == 1


# get_required_in_response


def test_get_required_in_response() -> None:
    response: Response = {"key": "value"}
    assert get_required_in_response(["key"], response) == ("value",)


def test_get_required_in_response_error() -> None:
    response: Response = {}
    with raises(ApiResponseError) as exc_info:
        get_required_in_response(["key"], response)

    assert len(exc_info.value.args) == 1
    assert exc_info.value.args[0] == "The following information was not returned: ['key']"


# perform_request


def test_perform_request_post_request() -> None:
    url: str = "http://localhost"
    with Mocker() as mock:
        mock.post(url, status_code=200, json={})
        response: tuple(Response, str) = perform_request(endpoint=url, headers={}, method="post")
        assert response[0] == {}


def test_perform_request_put_request() -> None:
    url: str = "http://localhost"
    response_json: Dict = {"status": 200}
    with Mocker() as mock:
        response: _Matcher = mock.put(url, status_code=200, json={})
        perform_request(endpoint=url, headers={}, method="put")

        assert response.called == True


def test_perform_request_delete_request() -> None:
    url: str = "http://localhost"
    with Mocker() as mock:
        response: _Matcher = mock.delete(url, status_code=200, json={})
        perform_request(endpoint=url, headers={}, method="delete")

        assert response.called == True


def test_perform_request_error() -> None:
    url: str = "http://localhost"
    with Mocker() as mock:
        mock.get(url, status_code=404, json={})
        with raises(DDSCLIException) as exc_info:
            perform_request(
                endpoint=url,
                headers={},
                method="get",
            )

        assert len(exc_info.value.args) == 1
        assert exc_info.value.args[0] == "API Request failed.: Unexpected error!"


def test_perform_request_request_exception() -> None:
    with raises(ApiRequestError) as exc_info:
        perform_request(
            endpoint="http://localhost",
            headers={},
            method="get",
        )

    assert len(exc_info.value.args) == 1
    assert "API Request failed.: The database seems to be down" in exc_info.value.args[0]


def test_perform_request_api_response_error_internal_server_error() -> None:
    url: str = "http://localhost"
    response_json: Dict = {
        "status": 500,
    }
    with Mocker() as mock:
        mock.get(url, status_code=500, json=response_json)
        with raises(ApiResponseError) as exc_info:
            perform_request(
                endpoint=url,
                headers={},
                method="get",
                error_message="Error",
            )

        assert len(exc_info.value.args) == 1
        assert exc_info.value.args[0] == "Error: None"


def test_perform_request_project_creation_error() -> None:
    response_json: Dict = {
        "message": "message",
        "title": "",
        "description": "",
        "pi": "",
        "email": "",
    }
    with Mocker() as mock:
        mock.post(DDSEndpoint.CREATE_PROJ, status_code=400, json=response_json)
        with raises(DDSCLIException) as exc_info:
            _: tuple(Response, str) = perform_request(
                endpoint=DDSEndpoint.CREATE_PROJ, headers={}, method="post"
            )

        assert len(exc_info.value.args) == 1
        assert exc_info.value.args[0] == "API Request failed.: message"


def test_perform_request_project_creation_error_list() -> None:
    response_json: Dict = {
        "message": ["message"],
        "title": "",
        "description": "",
        "pi": "",
        "email": "",
    }
    with Mocker() as mock:
        mock.post(DDSEndpoint.CREATE_PROJ, status_code=400, json=response_json)
        with raises(DDSCLIException) as exc_info:
            _: tuple(Response, str) = perform_request(
                endpoint=DDSEndpoint.CREATE_PROJ, headers={}, method="post"
            )

        assert len(exc_info.value.args) == 1
        assert exc_info.value.args[0] == "API Request failed.: message"


def test_perform_request_project_creation_error_insufficient_credentials() -> None:
    response_json: Dict = {
        "message": "You do not have the required permissions to create a project.",
        "title": "",
        "description": "",
        "pi": "",
        "email": "",
    }
    with Mocker() as mock:
        mock.post(DDSEndpoint.CREATE_PROJ, status_code=403, json=response_json)
        with raises(DDSCLIException) as exc_info:
            _: tuple(Response, str) = perform_request(
                endpoint=DDSEndpoint.CREATE_PROJ, headers={}, method="post"
            )

        assert len(exc_info.value.args) == 1
        assert (
            exc_info.value.args[0]
            == "API Request failed.: You do not have the required permissions to create a project."
        )


def test_perform_request_add_motd_error_insufficient_credentials() -> None:
    response_json: Dict = {
        "message": "Only Super Admin can add a MOTD.",
        "title": "",
        "description": "",
        "pi": "",
        "email": "",
    }
    with Mocker() as mock:
        mock.post(DDSEndpoint.MOTD, status_code=403, json=response_json)
        with raises(DDSCLIException) as exc_info:
            _: tuple(Response, str) = perform_request(
                endpoint=DDSEndpoint.MOTD, headers={}, method="post"
            )

        assert len(exc_info.value.args) == 1
        assert exc_info.value.args[0] == "API Request failed.: Only Super Admin can add a MOTD."


def test_perform_request_project_access_errors() -> None:
    """Test that the `errors` in the response are parsed in the correct way."""
    response_json: Dict = {
        "email": "test@mail.com",
        "errors": {"project_1": "test message", "project_2": "test message"},
        "status": 400,
    }
    with Mocker() as mock:
        mock.post(DDSEndpoint.PROJ_ACCESS, status_code=400, json=response_json)
        with raises(DDSCLIException) as exc_info:
            _: tuple(Response, str) = perform_request(
                endpoint=DDSEndpoint.PROJ_ACCESS,
                headers={},
                method="post",
                error_message="Project access error",
            )

        # Make sure that errors are parsed correctly
        assert "Project access error\ntest message\n   - project_1\n   - project_2" in str(
            exc_info.value
        )


def test_perform_request_add_user_errors() -> None:
    """Attempt to invite user, but the user does not have access."""
    response_json: Dict = {
        "email": "test_email@mail.com",
        "message": "test message",
        "status": 400,
        "errors": {"project_1": "test message", "project_2": "test message"},
    }
    with Mocker() as mock:
        mock.post(DDSEndpoint.USER_ADD, status_code=400, json=response_json)
        with raises(DDSCLIException) as exc_info:
            _: tuple(Response, str) = perform_request(
                endpoint=DDSEndpoint.USER_ADD,
                headers={},
                method="post",
                error_message="Invite error",
            )

        # Make sure that errors are parsed correctly
        assert "Invite error\ntest message\n   - project_1\n   - project_2" in str(exc_info.value)


def test_perform_request_activate_TOTP_error() -> None:
    response_json: Dict = {
        "message": "test message",
        "title": "",
        "description": "",
        "pi": "",
        "email": "",
    }
    with Mocker() as mock:
        mock.post(DDSEndpoint.USER_ACTIVATE_TOTP, status_code=400, json=response_json)
        with raises(DDSCLIException) as exc_info:
            perform_request(endpoint=DDSEndpoint.USER_ACTIVATE_TOTP, headers={}, method="post")

        assert len(exc_info.value.args) == 1
        assert exc_info.value.args[0] == "API Request failed.: test message"


def test_perform_request_activate_HOTP_error() -> None:
    response_json: Dict = {
        "message": "test message",
        "title": "",
        "description": "",
        "pi": "",
        "email": "",
    }
    with Mocker() as mock:
        mock.post(DDSEndpoint.USER_ACTIVATE_HOTP, status_code=400, json=response_json)
        with raises(DDSCLIException) as exc_info:
            perform_request(endpoint=DDSEndpoint.USER_ACTIVATE_HOTP, headers={}, method="post")

        assert len(exc_info.value.args) == 1
        assert exc_info.value.args[0] == "API Request failed.: test message"


def test_perform_request_custom_header_message(caplog: LogCaptureFixture) -> None:
    url: str = "http://localhost"
    with Mocker() as mock:
        with pytest.raises(DDSCLIException) as err:
            mock.get(url, status_code=403, json={"message": "this is a special testing message"})
            perform_request(endpoint=url, method="get")

        assert "this is a special testing message" in str(err.value)


# TODO: parse_project_errors

# multiple_help_text


def test_multiple_help_text() -> None:
    assert (
        multiple_help_text("")
        == " Use the option multiple times to specify more than one  [multiple]"
    )


# get_json_response


def test_get_json_response() -> None:
    url: str = "http://localhost"

    with Mocker() as mock:
        mock.get(url, status_code=200, json={})
        response: Response = get(url)
        response_json: Dict = get_json_response(response)

        assert type(response_json) == dict
        assert response_json == {}


def test_get_json_response_error(capsys: CaptureFixture) -> None:
    url: str = "http://localhost"

    with Mocker() as mock:
        mock.get(url, status_code=200, text="text")
        response: Response = get(url)
        with raises(SystemExit) as exc_info:
            response_json: Dict = get_json_response(response)

            assert type(response_json) == Dict
            assert response_json == {}

    # Get stderr
    captured = capsys.readouterr()

    assert captured.out == ""
    assert captured.err == ""

    assert exc_info.type == SystemExit
    assert exc_info.value.code == None
    assert len(exc_info.value.args) == 0


# format_api_response


def test_format_api_response_boolean_true() -> None:
    assert (
        format_api_response(response=True, key="", binary=True, always_show=True)
        == ":white_heavy_check_mark:"
    )


def test_format_api_response_boolean_false() -> None:
    assert format_api_response(response=False, key="", binary=False, always_show=False) == ":x:"


def test_format_api_response_number_size() -> None:
    assert format_api_response(response=0, key="Size", binary=False, always_show=False) == "0.0 B"


def test_format_api_response_number_size_negative() -> None:
    assert format_api_response(response=-1, key="Size", binary=False, always_show=False) == "-1.0 B"


def test_format_api_response_number() -> None:
    assert format_api_response(response=0, key="Cost", binary=False, always_show=False) == "0.0 kr"


def test_format_api_response_bytes_binary() -> None:
    assert (
        format_api_response(response=5000000000, key="Usage", binary=True, always_show=False)
        == "4.7 GiBH"
    )


def test_format_api_response_cost() -> None:
    assert (
        format_api_response(response=1000000, key="Cost", binary=False, always_show=False)
        == "1.0 Mkr"
    )


# get_token_header_contents


def test_get_token_header_contents_exception() -> None:
    with raises(TokenDeserializationError) as error:
        get_token_header_contents(token="not.a.token")

    assert "Token could not be deserialized" in str(error.value)

    with raises(TokenDeserializationError) as error:
        get_token_header_contents(token="notatoken")

    assert "Token could not be deserialized" in str(error.value)

    with raises(TokenDeserializationError) as error:
        get_token_header_contents(token="not.a.token.not.a")

    assert "Token could not be deserialized" in str(error.value)


# get_token_expiration_time


def test_get_token_expiration_time_successful() -> None:
    exp_claim_in_token_header = get_token_expiration_time(token=sample_fully_authenticated_token)
    assert isinstance(datetime.fromisoformat(exp_claim_in_token_header), datetime)


def test_get_token_expiration_time_exception() -> None:
    with raises(TokenExpirationMissingError) as error:
        get_token_expiration_time(token=token_without_exp_claim_in_header)

    assert "Expiration time could not be found in the header of the token." in str(error.value)


# readable_timedelta


def test_readable_timedelta() -> None:
    assert readable_timedelta(timedelta(seconds=60)) == "1 minute"
    assert readable_timedelta(timedelta(milliseconds=-100)) == "less than a minute"

    assert readable_timedelta(timedelta(milliseconds=100)) == "less than a minute"
    assert readable_timedelta(timedelta(seconds=59)) == "less than a minute"
    assert readable_timedelta(timedelta(seconds=60)) == "1 minute"
    assert readable_timedelta(timedelta(minutes=1)) == "1 minute"
    assert readable_timedelta(timedelta(seconds=98765)) == "1 day 3 hours 26 minutes"
    assert readable_timedelta(timedelta(hours=3)) == "3 hours"
    assert readable_timedelta(timedelta(days=1)) == "1 day"


# get_deletion_confirmation


def test_get_deletion_confirmation() -> None:
    def ask(question: str) -> str:
        return "delete"

    def Confirm() -> str:
        return ""

    def prompt() -> str:
        return ""

    rich.prompt = prompt
    rich.prompt.Confirm = Confirm
    rich.prompt.Confirm.ask = ask

    assert get_deletion_confirmation("delete", "project") == "delete"


def test_get_deletion_confirmation_abort() -> None:
    def ask(question: str) -> str:
        return "abort"

    def Confirm() -> str:
        return ""

    def prompt() -> str:
        """"""

    rich.prompt = prompt
    rich.prompt.Confirm = Confirm
    rich.prompt.Confirm.ask = ask

    assert get_deletion_confirmation("delete", "project") == "abort"


# print_or_page


def test_print_or_page() -> None:
    table = Table()
    table.add_column()

    # Get stdout
    output: StringIO = StringIO()
    sys.stdout = output

    print_or_page(table)

    sys.stdout = sys.__stdout__

    assert len(output.getvalue()) == 20


def test_print_or_page_multiple_rows() -> None:
    table = Table()
    table.add_column()
    for i in range(0, 100):
        table.add_row()

    # Get stdout
    output: StringIO = StringIO()
    sys.stdout = output

    print_or_page(table)

    sys.stdout = sys.__stdout__

    assert len(output.getvalue()) == 520


def test_print_or_page_error() -> None:
    table = Table()
    with raises(NoDataError) as exc_info:
        print_or_page(table)

    assert len(exc_info.value.args) == 1
    assert exc_info.value.args[0] == "No users found."


# delete_folder


def test_delete_folder(fs: FakeFilesystem) -> None:
    fs.create_dir("folder")
    fs.create_file("folder/file")
    assert path.isdir("folder") == True
    delete_folder("folder")
    assert path.isdir("folder") == False


def test_delete_folder_folder(fs: FakeFilesystem) -> None:
    fs.create_dir("folder/folder")
    fs.create_file("folder/file")
    assert path.isdir("folder") == True
    delete_folder("folder")
    assert path.isdir("folder") == False
