import pytest
from requests_mock.mocker import Mocker
from dds_cli import DDSEndpoint
from dds_cli import project_status
from _pytest.logging import LogCaptureFixture
from _pytest.capture import CaptureFixture
import logging
from dds_cli.exceptions import ApiResponseError, DDSCLIException

import typing

# init

#########

project_name = "Test"
returned_response_get_info: typing.Dict = {
    "Project ID": "Test001",
    "Created by": "Mr Bean",
    "Status": "In progress",
    "Last updated": "None",
    "Size": "0.0 B",
    "Title": "Test",
    "Description": "a description",
    "PI": "pi@a.se",
}
returned_response_archived_ok: typing.Dict = {
    "message": f"{project_name} updated to status Archived. An e-mail notification has been sent."
}
returned_response_deleted_ok: typing.Dict = {
    "message": f"{project_name} updated to status Deleted. An e-mail notification has been sent."
}
returned_response_available_ok: typing.Dict = {
    "message": f"{project_name} updated to status Available. An e-mail notification has been sent."
}

#########


def perform_archive_delete_operation(new_status, confirmed, mock, json_project_info=None):
    returned_response: typing.Dict = {
        "message": f"{project_name} updated to status {new_status}. An e-mail notification has been sent."
    }

    if not json_project_info:
        json_project_info = {"project_info": returned_response_get_info}

    # Create mocked request - real request not executed
    mock.get(
        DDSEndpoint.PROJ_INFO,
        status_code=200,
        json=json_project_info,
    )
    mock.post(DDSEndpoint.UPDATE_PROJ_STATUS, status_code=200, json=returned_response)

    if not confirmed:
        # capture system exit on not accepting operation
        with pytest.raises(SystemExit):
            with project_status.ProjectStatusManager(
                project=project_name, no_prompt=True, authenticate=False
            ) as status_mngr:
                status_mngr.token = {}  # required, otherwise none
                status_mngr.update_status(new_status=new_status)
    else:
        with project_status.ProjectStatusManager(
            project=project_name, no_prompt=True, authenticate=False
        ) as status_mngr:
            status_mngr.token = {}  # required, otherwise none
            status_mngr.update_status(new_status=new_status)


def check_output_project_info(new_status, captured_output, caplog_tuples=None):
    # Becuase of the bold and coloring formating, it is better to test for this keyworkd. Insetad of trying to find
    # the whole string The project 'project_1' is about to be Deleted.
    assert f"{project_name}" in captured_output.out
    assert f"{new_status}"

    assert "┏━━━━━" in captured_output.out  # A table has generated
    assert f"{returned_response_get_info['Project ID']}" in captured_output.out
    assert f"{returned_response_get_info['Created by']}" in captured_output.out
    assert f"{returned_response_get_info['Status']}" in captured_output.out
    assert f"{returned_response_get_info['Last updated']}" in captured_output.out
    assert f"{returned_response_get_info['Size']}" in captured_output.out

    # if not confirmed operation
    if caplog_tuples:
        assert (
            "dds_cli.project_status",
            logging.INFO,
            "Probably for the best. Exiting.",
        ) in caplog_tuples


# tests


def test_init_project_status_manager():
    """Create manager."""
    status_mngr: project_status.ProjectStatusManager = project_status.ProjectStatusManager(
        project=project_name, no_prompt=True, authenticate=False
    )
    assert isinstance(status_mngr, project_status.ProjectStatusManager)


def test_fail_update_project(capsys: CaptureFixture):
    """Test that fails when trying to update the project status"""

    # Create mocker
    with Mocker() as mock:
        # Create mocked request - real request not executed
        mock.get(DDSEndpoint.PROJ_INFO, status_code=200, json={})
        mock.post(DDSEndpoint.UPDATE_PROJ_STATUS, status_code=403, json={})

        with pytest.raises(DDSCLIException) as err:
            with project_status.ProjectStatusManager(
                project=project_name, no_prompt=True, authenticate=False
            ) as status_mngr:
                status_mngr.token = {}  # required, otherwise none
                status_mngr.update_status(new_status="Available")

        assert "Failed to update project status" in str(err.value)


def test_fail_display_project_info(capsys: CaptureFixture):
    """Test that fails when trying to retrieve the project info to display"""

    # Create mocker
    with Mocker() as mock:
        # Create mocked request - real request not executed
        mock.get(DDSEndpoint.PROJ_INFO, status_code=403, json={})
        mock.post(DDSEndpoint.UPDATE_PROJ_STATUS, status_code=200, json={})

        with pytest.raises(DDSCLIException) as err:
            with project_status.ProjectStatusManager(
                project=project_name, no_prompt=True, authenticate=False
            ) as status_mngr:
                status_mngr.token = {}  # required, otherwise none
                status_mngr.update_status(new_status="Archived")

        assert "Failed to get project information:" in str(err.value)


def test_release_project(capsys: CaptureFixture):
    """Test that tries to release a project and seeting up as available"""

    # Create mocker
    with Mocker() as mock:
        # Create mocked request - real request not executed
        mock.get(DDSEndpoint.PROJ_INFO, status_code=200, json={})
        mock.post(
            DDSEndpoint.UPDATE_PROJ_STATUS,
            status_code=200,
            json=returned_response_available_ok,
        )

        with project_status.ProjectStatusManager(
            project=project_name, no_prompt=True, authenticate=False
        ) as status_mngr:
            status_mngr.token = {}  # required, otherwise none
            status_mngr.update_status(new_status="Available")

        assert returned_response_available_ok["message"] in capsys.readouterr().out


def test_delete_project_no(capsys: CaptureFixture, monkeypatch, caplog: LogCaptureFixture):
    """Test that tries to delete a project, but the user selects no to perfrom the operation"""

    confirmed = False
    caplog.set_level(logging.INFO)
    # Create mocker
    with Mocker() as mock:
        # set confirmation object to false
        monkeypatch.setattr("rich.prompt.Confirm.ask", lambda question: confirmed)
        perform_archive_delete_operation(new_status="Deleted", confirmed=confirmed, mock=mock)
        captured_output = capsys.readouterr()

        # for some reason the captured log includees line break here. But in the client it displays normal ->
        # could be because of the if-else to build this log
        assert (
            f"Are you sure you want to modify the status of {project_name}? All its contents and \nmetainfo will be deleted!"
            in captured_output.out
        )

        # check the rest of the project info is displayed correctly
        check_output_project_info(
            new_status="Deleted",
            captured_output=captured_output,
            caplog_tuples=caplog.record_tuples,
        )


def test_archive_project_no(capsys: CaptureFixture, monkeypatch, caplog: LogCaptureFixture):
    """Test that tries to archive a project, but the user selects no to perfrom the operation"""

    confirmed = False
    caplog.set_level(logging.INFO)
    # Create mocker
    with Mocker() as mock:
        # set confirmation object to false
        monkeypatch.setattr("rich.prompt.Confirm.ask", lambda question: confirmed)
        perform_archive_delete_operation(new_status="Archived", confirmed=confirmed, mock=mock)
        captured_output = capsys.readouterr()

        # for some reason the captured log includees line break here. But in the client it displays normal ->
        # could be because of the if-else to build this log
        assert (
            f"Are you sure you want to modify the status of {project_name}? All its contents will be \ndeleted!"
            in captured_output.out
        )

        # check the rest of the project info is displayed correctly
        check_output_project_info(
            new_status="Archived",
            captured_output=captured_output,
            caplog_tuples=caplog.record_tuples,
        )


def test_delete_project_yes(capsys: CaptureFixture, monkeypatch, caplog: LogCaptureFixture):
    """Test that tries to delete a project, the user accepts the operation"""

    confirmed = True
    # Create mocker
    with Mocker() as mock:
        # set confirmation object to true
        monkeypatch.setattr("rich.prompt.Confirm.ask", lambda question: confirmed)
        perform_archive_delete_operation(new_status="Deleted", confirmed=confirmed, mock=mock)
        captured_output = capsys.readouterr()

        assert returned_response_deleted_ok["message"] in captured_output.out
        # check the rest of the project info is displayed correctly
        check_output_project_info(
            new_status="Deleted", captured_output=captured_output, caplog_tuples=None
        )


def test_archive_project_yes(capsys: CaptureFixture, monkeypatch, caplog: LogCaptureFixture):
    """Test that tries to archive a project, the user accepts the operation"""

    confirmed = True
    # Create mocker
    with Mocker() as mock:
        # set confirmation object to true
        monkeypatch.setattr("rich.prompt.Confirm.ask", lambda question: confirmed)
        perform_archive_delete_operation(new_status="Archived", confirmed=confirmed, mock=mock)
        captured_output = capsys.readouterr()

        assert returned_response_archived_ok["message"] in captured_output.out
        check_output_project_info(
            new_status="Archived", captured_output=captured_output, caplog_tuples=None
        )


def test_no_project_info(capsys: CaptureFixture, monkeypatch):
    """Test that check when it returns no project info during request"""

    confirmed = True
    # Create mocker
    with Mocker() as mock:
        # set confirmation object to True
        monkeypatch.setattr("rich.prompt.Confirm.ask", lambda question: True)

        perform_archive_delete_operation(
            new_status="Archived",
            confirmed=confirmed,
            mock=mock,
            json_project_info={"project_info": {}},
        )
        assert (
            "No project information could be displayed at this moment!. You can continue with the operation if you want"
            in capsys.readouterr().out
        )


def test_update_extra_params(capsys: CaptureFixture, monkeypatch, caplog: LogCaptureFixture):
    """Test that update the project status providing extra params"""

    # Create mocker
    with Mocker() as mock:
        # Create mocked request - real request not executed
        mock.get(
            DDSEndpoint.PROJ_INFO,
            status_code=200,
            json={"project_info": returned_response_get_info},
        )
        mock.post(
            DDSEndpoint.UPDATE_PROJ_STATUS,
            status_code=200,
            json=returned_response_archived_ok,
        )
        monkeypatch.setattr("rich.prompt.Confirm.ask", lambda question: True)

        with project_status.ProjectStatusManager(
            project=project_name, no_prompt=True, authenticate=False
        ) as status_mngr:
            status_mngr.token = {}  # required, otherwise none
            status_mngr.update_status(new_status="Archived", is_aborted=True, deadline=10)

        assert returned_response_archived_ok["message"] in capsys.readouterr().out
