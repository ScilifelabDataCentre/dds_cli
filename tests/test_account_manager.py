from _pytest.logging import LogCaptureFixture
from pyfakefs.fake_filesystem import FakeFilesystem
from dds_cli import account_manager
from dds_cli import utils
from typing import Dict
from requests_mock.mocker import Mocker
from dds_cli import DDSEndpoint
from dds_cli import exceptions
import pytest
import pathlib


from dds_cli.__main__ import LOG


def test_list_users_no_unit_none_response(fs: FakeFilesystem):
    # Set response in mocked request
    response_json: Dict = None

    # Create mocker
    with Mocker() as mock:
        # Create mocked request - real request not executed
        mock.get(DDSEndpoint.LIST_USERS, status_code=200, json=response_json)

        # perform_request should raise an error
        with pytest.raises(exceptions.ApiResponseError) as exc_info:
            # Create accountmanager needed for access to list_users and set token to dict
            with account_manager.AccountManager(authenticate=False, no_prompt=True) as acm:
                acm.token = {}  # required, otherwise none
                acm.list_users()  # run list users


def test_list_users_no_unit_empty_response(fs: FakeFilesystem):
    # Set response in mocked request
    response_json: Dict = {}

    # Create mocker
    with Mocker() as mock:
        # Create mocked request - real request not executed
        mock.get(DDSEndpoint.LIST_USERS, status_code=200, json=response_json)

        # perform_request should raise an error
        with pytest.raises(exceptions.ApiResponseError) as exc_info:
            # Create accountmanager needed for access to list_users and set token to dict
            with account_manager.AccountManager(authenticate=False, no_prompt=True) as acm:
                acm.token = {}  # required, otherwise none
                acm.list_users()  # run list users

        assert "The following information was not returned: ['users', 'keys']" in str(
            exc_info.value
        )

def test_save_emails_empty_response(fs: FakeFilesystem, caplog: LogCaptureFixture):
    """No file should be created if no emails are returned."""
    # Verify that file doesn't exist
    non_existent_file: pathlib.Path = pathlib.Path("unit_user_emails.txt")
    assert not fs.exists(file_path=non_existent_file)

    # Return empty
    response_json: Dict = {}

    # Create mocker
    with Mocker() as mock:
        # Create mocked request - real request not executed
        mock.get(DDSEndpoint.USER_EMAILS, status_code=200, json=response_json)

        # perform_request should raise an error
        with pytest.raises(exceptions.ApiResponseError) as exc_info:
            # Create accountmanager 'needed for access to list_users and set token to dict
            with account_manager.AccountManager(authenticate=False, no_prompt=True) as acm:
                acm.token = {}  # required, otherwise none
                acm.save_emails()  # run l'ist users

        assert "No information returned from the API. Could not get user emails." in str(
            exc_info.value
        )