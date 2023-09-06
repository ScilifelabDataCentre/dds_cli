import pytest
from requests_mock.mocker import Mocker
from dds_cli import DDSEndpoint
from dds_cli import superadmin_helper
from _pytest.logging import LogCaptureFixture
import logging
from dds_cli.exceptions import ApiResponseError

import typing

# init


def test_init_maintenance_manager():
    """Create manager."""
    maint_mngr: superadmin_helper.SuperAdminHelper = superadmin_helper.SuperAdminHelper(
        authenticate=False, no_prompt=True
    )
    assert isinstance(maint_mngr, superadmin_helper.SuperAdminHelper)


# change_maintenance_mode


def test_change_maintenance_mode_no_response(caplog: LogCaptureFixture):
    """No response from API."""
    returned_response: typing.Dict = {}
    with caplog.at_level(logging.INFO):
        # Create mocker
        with Mocker() as mock:
            # Create mocked request - real request not executed
            mock.put(DDSEndpoint.MAINTENANCE, status_code=200, json=returned_response)

            with superadmin_helper.SuperAdminHelper(
                authenticate=False, no_prompt=True
            ) as maint_mngr:
                maint_mngr.token = {}  # required, otherwise none
                maint_mngr.change_maintenance_mode(setting="on")  # Run deactivation

            assert (
                "dds_cli.superadmin_helper",
                logging.INFO,
                "No response. Cannot confirm setting maintenance mode.",
            ) in caplog.record_tuples


def test_get_maintenance_mode_status_no_response(caplog: LogCaptureFixture):
    """No response from API when getting mode status."""
    returned_response: typing.Dict = {}
    with caplog.at_level(logging.INFO):
        # Create mocker
        with Mocker() as mock:
            # Create mocked request - real request not executed
            mock.get(DDSEndpoint.MAINTENANCE, status_code=200, json=returned_response)

            with superadmin_helper.SuperAdminHelper(
                authenticate=False, no_prompt=True
            ) as maint_mngr:
                maint_mngr.token = {}  # required, otherwise none
                maint_mngr.display_maintenance_mode_status()

            assert (
                "dds_cli.superadmin_helper",
                logging.INFO,
                "No response. Cannot display maintenance mode status.",
            ) in caplog.record_tuples


def test_activate_maintenance_ok(caplog: LogCaptureFixture):
    """Set maintenance mode to ON."""
    returned_response: typing.Dict = {"message": "Message from API about mode change."}
    with caplog.at_level(logging.INFO):
        # Create mocker
        with Mocker() as mock:
            # Create mocked request - real request not executed
            mock.put(DDSEndpoint.MAINTENANCE, status_code=200, json=returned_response)

            with superadmin_helper.SuperAdminHelper(
                authenticate=False, no_prompt=True
            ) as maint_mngr:
                maint_mngr.token = {}  # required, otherwise none
                maint_mngr.change_maintenance_mode(setting="on")  # Run deactivation

            assert (
                "dds_cli.superadmin_helper",
                logging.INFO,
                "Message from API about mode change.",
            ) in caplog.record_tuples


def test_deactivate_maintenance_ok(caplog: LogCaptureFixture):
    """Set maintenance mode to OFF."""
    returned_response: typing.Dict = {"message": "Message from API about mode change."}
    with caplog.at_level(logging.INFO):
        # Create mocker
        with Mocker() as mock:
            # Create mocked request - real request not executed
            mock.put(DDSEndpoint.MAINTENANCE, status_code=200, json=returned_response)

            with superadmin_helper.SuperAdminHelper(
                authenticate=False, no_prompt=True
            ) as maint_mngr:
                maint_mngr.token = {}  # required, otherwise none
                maint_mngr.change_maintenance_mode(setting="on")  # Run deactivation

            assert (
                "dds_cli.superadmin_helper",
                logging.INFO,
                "Message from API about mode change.",
            ) in caplog.record_tuples


def test_get_maintenance_mode_status_ok(caplog: LogCaptureFixture):
    """Check current maintenance mode status."""
    returned_response: typing.Dict = {"message": "Message from API about mode status."}
    with caplog.at_level(logging.INFO):
        # Create mocker
        with Mocker() as mock:
            # Create mocked request - real request not executed
            mock.get(DDSEndpoint.MAINTENANCE, status_code=200, json=returned_response)

            with superadmin_helper.SuperAdminHelper(
                authenticate=False, no_prompt=True
            ) as maint_mngr:
                maint_mngr.token = {}  # required, otherwise none
                maint_mngr.display_maintenance_mode_status()  # Run deactivation

            assert (
                "dds_cli.superadmin_helper",
                logging.INFO,
                "Message from API about mode status.",
            ) in caplog.record_tuples


def test_get_stats(caplog: LogCaptureFixture):
    """Print stats."""
    returned_response: typing.Dict = {}
    with caplog.at_level(logging.INFO):
        # Create mocker
        with Mocker() as mock:
            # Create mocked request - real request not executed
            mock.get(DDSEndpoint.STATS, status_code=200, json=returned_response)

            with pytest.raises(ApiResponseError) as err:
                with superadmin_helper.SuperAdminHelper(
                    authenticate=False, no_prompt=True
                ) as helper:
                    helper.token = {}  # required, otherwise none
                    helper.get_stats()  # Get stats

            assert "The following information was not returned: ['stats', 'columns']" in str(
                err.value
            )
