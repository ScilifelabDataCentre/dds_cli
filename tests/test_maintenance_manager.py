import pytest
from requests_mock.mocker import Mocker
from dds_cli import DDSEndpoint
from dds_cli import maintenance_manager
from _pytest.logging import LogCaptureFixture
import logging
from dds_cli.exceptions import InvalidMethodError

# init


def test_init_maintenance_manager_incorrect_method():
    """Init with incorrect method."""
    method = "rm"
    with pytest.raises(InvalidMethodError) as err:
        _: maintenance_manager.MaintenanceManager = maintenance_manager.MaintenanceManager(
            method=method, authenticate=False, no_prompt=True
        )

    assert f"Unauthorized method: '{method}'" in str(err.value)


def test_init_maintenance_manager():
    """Create manager."""
    maint_mngr: maintenance_manager.MaintenanceManager = maintenance_manager.MaintenanceManager(
        authenticate=False, no_prompt=True
    )
    assert isinstance(maint_mngr, maintenance_manager.MaintenanceManager)


# change_maintenance_mode


def test_change_maintenance_mode_no_response(caplog: LogCaptureFixture):
    """No response from API."""
    returned_response: Dict = {}
    with caplog.at_level(logging.INFO):
        # Create mocker
        with Mocker() as mock:
            # Create mocked request - real request not executed
            mock.put(DDSEndpoint.MAINTENANCE, status_code=200, json=returned_response)

            with maintenance_manager.MaintenanceManager(
                authenticate=False, no_prompt=True
            ) as maint_mngr:
                maint_mngr.token = {}  # required, otherwise none
                maint_mngr.change_maintenance_mode(setting="on")  # Run deactivation

            assert (
                "dds_cli.maintenance_manager",
                logging.INFO,
                "No response. Cannot confirm setting maintenance mode.",
            ) in caplog.record_tuples


def test_activate_maintenance_ok(caplog: LogCaptureFixture):
    """Set maintenance mode to ON."""
    returned_response: Dict = {"message": "Message from API about mode change."}
    with caplog.at_level(logging.INFO):
        # Create mocker
        with Mocker() as mock:
            # Create mocked request - real request not executed
            mock.put(DDSEndpoint.MAINTENANCE, status_code=200, json=returned_response)

            with maintenance_manager.MaintenanceManager(
                authenticate=False, no_prompt=True
            ) as maint_mngr:
                maint_mngr.token = {}  # required, otherwise none
                maint_mngr.change_maintenance_mode(setting="on")  # Run deactivation

            assert (
                "dds_cli.maintenance_manager",
                logging.INFO,
                "Message from API about mode change.",
            ) in caplog.record_tuples


def test_deactivate_maintenance_ok(caplog: LogCaptureFixture):
    """Set maintenance mode to OFF."""
    returned_response: Dict = {"message": "Message from API about mode change."}
    with caplog.at_level(logging.INFO):
        # Create mocker
        with Mocker() as mock:
            # Create mocked request - real request not executed
            mock.put(DDSEndpoint.MAINTENANCE, status_code=200, json=returned_response)

            with maintenance_manager.MaintenanceManager(
                authenticate=False, no_prompt=True
            ) as maint_mngr:
                maint_mngr.token = {}  # required, otherwise none
                maint_mngr.change_maintenance_mode(setting="on")  # Run deactivation

            assert (
                "dds_cli.maintenance_manager",
                logging.INFO,
                "Message from API about mode change.",
            ) in caplog.record_tuples
