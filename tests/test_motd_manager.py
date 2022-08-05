import pytest
from requests_mock.mocker import Mocker
from dds_cli import DDSEndpoint
from typing import Dict, List
from dds_cli import motd_manager
from _pytest.capture import CaptureFixture
from _pytest.logging import LogCaptureFixture
import logging
from dds_cli.exceptions import ApiResponseError, InvalidMethodError

# init


def test_init_motdmanager_incorrect_method():
    """Init with incorrect method."""
    method = "rm"
    with pytest.raises(InvalidMethodError) as err:
        _: motd_manager.MotdManager = motd_manager.MotdManager(
            method=method, authenticate=False, no_prompt=True
        )

    assert f"Unauthorized method: '{method}'" in str(err.value)


def test_init_motdmanager():
    """Create manager."""
    motdmanager: motd_manager.MotdManager = motd_manager.MotdManager(
        authenticate=False, no_prompt=True
    )
    assert isinstance(motdmanager, motd_manager.MotdManager)


# list_all_active_motds
def test_list_all_active_motds_no_motds(caplog: LogCaptureFixture):
    """No motds returned."""
    test_dicts: List[Dict] = [{}, {"message": "Test message when no motds."}, {"motds": {}}]
    with caplog.at_level(logging.INFO):
        # Iterate through possible alternative responses
        for retd in test_dicts:
            # Create mocker
            with Mocker() as mock:

                # Create mocked request - real request not executed
                mock.get(DDSEndpoint.MOTD, status_code=200, json=retd)

                with motd_manager.MotdManager(authenticate=False, no_prompt=True) as mtdm:
                    mtdm.list_all_active_motds(table=True)  # Run active motds listing

                assert (
                    "dds_cli.motd_manager",
                    logging.INFO,
                    retd.get("message", "No motds or info message returned from API."),
                ) in caplog.record_tuples


def test_list_all_active_motds_no_keys():
    """List motds without any keys returned."""
    returned_dict: Dict = {
        "motds": [{"MOTD ID": 1, "Message": "Test", "Created": "2022-08-05 08:31"}]
    }
    # Create mocker
    with Mocker() as mock:

        # Create mocked request - real request not executed
        mock.get(DDSEndpoint.MOTD, status_code=200, json=returned_dict)

        with pytest.raises(ApiResponseError) as err:
            with motd_manager.MotdManager(authenticate=False, no_prompt=True) as mtdm:
                mtdm.list_all_active_motds(table=True)  # Run active motds listing

        assert "The following information was not returned: ['keys']" in str(err.value)


def test_list_all_active_motds_table(capsys: CaptureFixture):
    """List motds without any keys returned."""
    returned_dict: Dict = {
        "motds": [
            {"MOTD ID": 1, "Message": "Test", "Created": "2022-08-05 08:31"},
            {"MOTD ID": 2, "Message": "Test 2", "Created": "2022-08-05 08:54"},
        ],
        "keys": ["MOTD ID", "Message", "Created"],
    }
    # Create mocker
    with Mocker() as mock:

        # Create mocked request - real request not executed
        mock.get(DDSEndpoint.MOTD, status_code=200, json=returned_dict)

        with motd_manager.MotdManager(authenticate=False, no_prompt=True) as mtdm:
            mtdm.list_all_active_motds(table=True)  # Run active motds listing

    captured = capsys.readouterr()
    assert (
        "\n".join(
            [
                "┏━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┓",
                "┃ MOTD ID ┃ Message ┃ Created          ┃",
                "┡━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━━━━━┩",
                "│ 1       │ Test    │ 2022-08-05 08:31 │",
                "│ 2       │ Test 2  │ 2022-08-05 08:54 │",
                "└─────────┴─────────┴──────────────────┘",
            ]
        )
        in captured.out
    )


def test_list_all_active_motds_nottable(capsys: CaptureFixture):
    """List motds without any keys returned."""
    returned_dict: Dict = {
        "motds": [
            {"MOTD ID": 1, "Message": "Test", "Created": "2022-08-05 08:31"},
            {"MOTD ID": 2, "Message": "Test 2", "Created": "2022-08-05 08:54"},
        ],
        "keys": ["MOTD ID", "Message", "Created"],
    }
    # Create mocker
    with Mocker() as mock:

        # Create mocked request - real request not executed
        mock.get(DDSEndpoint.MOTD, status_code=200, json=returned_dict)

        with motd_manager.MotdManager(authenticate=False, no_prompt=True) as mtdm:
            motds = mtdm.list_all_active_motds(table=False)  # Run active motds listing

    captured = capsys.readouterr()
    assert captured.out == ""

    assert all(x in motds for x in returned_dict["motds"])


def test_list_all_active_motds_exceptionraised(capsys: CaptureFixture):
    """List motds when exception raised."""
    returned_dict: Dict = {}
    # Create mocker
    with Mocker() as mock:

        # Create mocked request - real request not executed
        mock.get(DDSEndpoint.MOTD, status_code=500, json=returned_dict)

        with motd_manager.MotdManager(authenticate=False, no_prompt=True) as mtdm:
            motds = mtdm.list_all_active_motds(table=False)  # Run active motds listing
            assert not motds  # If exception raised, nothing happens because of pass


# deactivate_motd


def test_deactivate_motd_no_response(caplog: LogCaptureFixture):
    """No response from API."""
    returned_response: Dict = {}
    with caplog.at_level(logging.INFO):
        # Create mocker
        with Mocker() as mock:
            # Create mocked request - real request not executed
            mock.put(DDSEndpoint.MOTD, status_code=200, json=returned_response)

            with motd_manager.MotdManager(authenticate=False, no_prompt=True) as mtdm:
                mtdm.token = {}  # required, otherwise none
                mtdm.deactivate_motd(motd_id=1)  # Run deactivation

            assert (
                "dds_cli.motd_manager",
                logging.INFO,
                "No response. Cannot confirm MOTD deactivation.",
            ) in caplog.record_tuples


def test_deactivate_motd_ok(caplog: LogCaptureFixture):
    """No response from API."""
    returned_response: Dict = {"message": "Message from API about deactivation."}
    with caplog.at_level(logging.INFO):
        # Create mocker
        with Mocker() as mock:
            # Create mocked request - real request not executed
            mock.put(DDSEndpoint.MOTD, status_code=200, json=returned_response)

            with motd_manager.MotdManager(authenticate=False, no_prompt=True) as mtdm:
                mtdm.token = {}  # required, otherwise none
                mtdm.deactivate_motd(motd_id=1)  # Run deactivation

            assert (
                "dds_cli.motd_manager",
                logging.INFO,
                "Message from API about deactivation.",
            ) in caplog.record_tuples


# add_new_motd


def test_add_new_motd_no_response(caplog: LogCaptureFixture):
    """Add new MOTD without any returned response."""
    returned_response: Dict = {}
    with caplog.at_level(logging.INFO):
        # Create mocker
        with Mocker() as mock:
            # Create mocked request - real request not executed
            mock.post(DDSEndpoint.MOTD, status_code=200, json=returned_response)

            with motd_manager.MotdManager(authenticate=False, no_prompt=True) as mtdm:
                mtdm.token = {}  # required, otherwise none
                mtdm.add_new_motd(message="Adding this message as a MOTD.")  # Add motd

            assert (
                "dds_cli.motd_manager",
                logging.INFO,
                "No response. Cannot confirm MOTD creation.",
            ) in caplog.record_tuples


def test_add_new_motd_ok(caplog: LogCaptureFixture):
    """Add new MOTD without any returned response."""
    returned_response: Dict = {"message": "Response from API about adding a MOTD."}
    with caplog.at_level(logging.INFO):
        # Create mocker
        with Mocker() as mock:
            # Create mocked request - real request not executed
            mock.post(DDSEndpoint.MOTD, status_code=200, json=returned_response)

            with motd_manager.MotdManager(authenticate=False, no_prompt=True) as mtdm:
                mtdm.token = {}  # required, otherwise none
                mtdm.add_new_motd(message="Adding this message as a MOTD.")  # Add motd

            assert (
                "dds_cli.motd_manager",
                logging.INFO,
                "Response from API about adding a MOTD.",
            ) in caplog.record_tuples
