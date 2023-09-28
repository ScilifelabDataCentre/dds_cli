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


def perform_archive_delete_operation(new_status, confirmed, mock):
    returned_response: typing.Dict = {
        "message": f"{project_name} updated to status {new_status}. An e-mail notification has been sent."
    }

    # Create mocked request - real request not executed
    mock.get(
        DDSEndpoint.PROJ_INFO,
        status_code=200,
        json={"project_info": returned_response_get_info},
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


def check_output_project_info(captured_output, caplog_tuples=None):
    assert "The project 'Test' is about to be Deleted." in captured_output.out
    assert f"Title:  {returned_response_get_info['Title']}" in captured_output.out
    assert f"Description:    {returned_response_get_info['Description']}" in captured_output.out
    assert f"PI:     {returned_response_get_info['PI']}" in captured_output.out

    if caplog_tuples:
        assert (
            "dds_cli.project_status",
            logging.INFO,
            "Probably for the best. Exiting.",
        ) in caplog_tuples


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
            captured_output=captured_output, caplog_tuples=caplog.record_tuples
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
            captured_output=captured_output, caplog_tuples=caplog.record_tuples
        )


def test_delete_project_yes(capsys: CaptureFixture, monkeypatch, caplog: LogCaptureFixture):
    """Test that tries to delete a project, the user accepts the operation"""

    confirmed = True
    # Create mocker
    with Mocker() as mock:
        # set confirmation object to true
        monkeypatch.setattr("rich.prompt.Confirm.ask", lambda question: confirmed)
        perform_archive_delete_operation(new_status="Deleted", confirmed=confirmed, mock=mock)
        assert returned_response_deleted_ok["message"] in capsys.readouterr().out


def test_archive_project_yes(capsys: CaptureFixture, monkeypatch, caplog: LogCaptureFixture):
    """Test that tries to archive a project, the user accepts the operation"""

    confirmed = True
    # Create mocker
    with Mocker() as mock:
        # set confirmation object to true
        monkeypatch.setattr("rich.prompt.Confirm.ask", lambda question: confirmed)
        perform_archive_delete_operation(new_status="Archived", confirmed=confirmed, mock=mock)
        assert returned_response_archived_ok["message"] in capsys.readouterr().out


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
