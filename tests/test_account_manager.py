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
import logging


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


def test_save_emails_empty_response(fs: FakeFilesystem):
    """No file should be created if nothing is returned."""
    # Verify that file doesn't exist
    non_existent_file: pathlib.Path = pathlib.Path("unit_user_emails.txt")
    assert not fs.exists(file_path=non_existent_file)

    # Empty not returned and empty False
    for response_json in [{}, {"empty": False}]:
        # Create mocker
        with Mocker() as mock:
            # Create mocked request - real request not executed
            mock.get(DDSEndpoint.USER_EMAILS, status_code=200, json=response_json)

            with pytest.raises(exceptions.ApiResponseError) as exc_info:
                # Create accountmanager needed for access and set token to dict
                with account_manager.AccountManager(authenticate=False, no_prompt=True) as acm:
                    acm.token = {}  # required, otherwise none
                    acm.save_emails()  # run save emails

            assert "No information returned from the API. Could not get user emails." in str(
                exc_info.value
            )

        # Verify that the file still doesn't exist
        assert not fs.exists(file_path=non_existent_file)


def test_save_emails_no_emails(fs: FakeFilesystem, caplog: LogCaptureFixture):
    """No file should be created if nothing is returned."""
    # Verify that file doesn't exist
    non_existent_file: pathlib.Path = pathlib.Path("unit_user_emails.txt")
    assert not fs.exists(file_path=non_existent_file)

    # Empty not returned and empty False
    response_json = {"empty": True}

    # Create mocker
    with Mocker() as mock:
        # Create mocked request - real request not executed
        mock.get(DDSEndpoint.USER_EMAILS, status_code=200, json=response_json)

        with caplog.at_level(logging.INFO):
            # Create accountmanager needed for access and set token to dict
            with account_manager.AccountManager(authenticate=False, no_prompt=True) as acm:
                acm.token = {}  # required, otherwise none
                acm.save_emails()  # run save emails

        assert (
            "dds_cli.account_manager",
            logging.INFO,
            "There are no user emails to save.",
        ) in caplog.record_tuples

    # Verify that the file still doesn't exist
    assert not fs.exists(file_path=non_existent_file)


def test_save_emails_emails_returned(fs: FakeFilesystem, caplog: LogCaptureFixture):
    """No file should be created if nothing is returned."""
    # Verify that file doesn't exist
    file_to_save: pathlib.Path = pathlib.Path("unit_user_emails.txt")
    assert not fs.exists(file_path=file_to_save)

    # Empty not returned and empty False
    response_json = {"emails": ["emailone", "emailtwo", "emailthree", "emailfour"]}

    # Create mocker
    with Mocker() as mock:
        # Create mocked request - real request not executed
        mock.get(DDSEndpoint.USER_EMAILS, status_code=200, json=response_json)

        with caplog.at_level(logging.DEBUG):
            # Create accountmanager 'needed for access and set token to dict
            with account_manager.AccountManager(authenticate=False, no_prompt=True) as acm:
                acm.token = {}  # required, otherwise none
                acm.save_emails()  # run save emails

        assert (
            "dds_cli.account_manager",
            logging.DEBUG,
            "Saving emails to file...",
        ) in caplog.record_tuples
        assert (
            "dds_cli.account_manager",
            logging.INFO,
            f"Saved emails to file: {file_to_save}",
        ) in caplog.record_tuples

    # Verify that the file still doesn't exist
    assert fs.exists(file_path=file_to_save)

    # Read file and verify contents
    with file_to_save.open(mode="r", encoding="utf-8") as f:
        assert f.read() == "emailone; emailtwo; emailthree; emailfour"
