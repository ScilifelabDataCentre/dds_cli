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
returned_response_available_ok: typing.Dict = {
    "message": f"{project_name} updated to status Available. An e-mail notification has been sent."
}
returned_response_archived_ok: typing.Dict = {
    "message": f"{project_name} updated to status Archived. An e-mail notification has been sent."
}
returned_response_deleted_ok: typing.Dict = {
    "message": f"{project_name} updated to status Deleted. An e-mail notification has been sent."
}

#########

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
        mock.get(DDSEndpoint.PROJ_INFO, status_code=200, json=returned_response_get_info)
        mock.post(DDSEndpoint.UPDATE_PROJ_STATUS, status_code=403, json={})

        with pytest.raises(DDSCLIException) as err:
            with project_status.ProjectStatusManager(
                project=project_name, no_prompt=True, authenticate=False
            ) as status_mngr:
                status_mngr.token = {}  # required, otherwise none
                status_mngr.update_status(new_status="Available")

        assert "Failed to update project status" in str(err.value)


def test_release_project(capsys: CaptureFixture):
    """Test that tries to release a project and seeting up as available"""

    # Create mocker
    with Mocker() as mock:
        # Create mocked request - real request not executed
        mock.get(DDSEndpoint.PROJ_INFO, status_code=200, json=returned_response_get_info)
        mock.post(
            DDSEndpoint.UPDATE_PROJ_STATUS, status_code=200, json=returned_response_available_ok
        )

        with project_status.ProjectStatusManager(
            project=project_name, no_prompt=True, authenticate=False
        ) as status_mngr:
            status_mngr.token = {}  # required, otherwise none
            status_mngr.update_status(new_status="Available")

        assert returned_response_available_ok["message"] in capsys.readouterr().out


def test_archive_delete_project_no(capsys: CaptureFixture, monkeypatch, caplog: LogCaptureFixture):
    """Test that tries to archive/delete a project, but the user selects no to perfrom the operation"""

    caplog.set_level(logging.INFO)
    # Create mocker
    with Mocker() as mock:
        # Create mocked request - real request not executed
        mock.get(
            DDSEndpoint.PROJ_INFO,
            status_code=200,
            json={"project_info": returned_response_get_info},
        )
        mock.post(DDSEndpoint.UPDATE_PROJ_STATUS, status_code=200, json={})
        monkeypatch.setattr("rich.prompt.Confirm.ask", lambda question: False)

        # capture system exit on not accepting operation
        with pytest.raises(SystemExit):
            with project_status.ProjectStatusManager(
                project=project_name, no_prompt=True, authenticate=False
            ) as status_mngr:
                status_mngr.token = {}  # required, otherwise none
                status_mngr.update_status(new_status="Archived")

        captured_output = capsys.readouterr().out
        captured_output = captured_output.split("\n")

        assert (
            f"Are you sure you want to modify the status of {project_name}? All its contents will be deleted!"
            in captured_output[0]
        )
        assert f"Title:  {returned_response_get_info['Title']}" in captured_output[2]
        assert f"Description:    {returned_response_get_info['Description']}" in captured_output[3]
        assert f"PI:     {returned_response_get_info['PI']}" in captured_output[4]

        assert (
            "dds_cli.project_status",
            logging.INFO,
            "Probably for the best. Exiting.",
        ) in caplog.record_tuples


def test_archive_delete_project_yes(capsys: CaptureFixture, monkeypatch, caplog: LogCaptureFixture):
    """Test that tries to archive/delete a project, the user accepts the operation"""

    # Create mocker
    with Mocker() as mock:
        # Create mocked request - real request not executed
        mock.get(
            DDSEndpoint.PROJ_INFO,
            status_code=200,
            json={"project_info": returned_response_get_info},
        )
        mock.post(
            DDSEndpoint.UPDATE_PROJ_STATUS, status_code=200, json=returned_response_archived_ok
        )
        monkeypatch.setattr("rich.prompt.Confirm.ask", lambda question: True)

        with project_status.ProjectStatusManager(
            project=project_name, no_prompt=True, authenticate=False
        ) as status_mngr:
            status_mngr.token = {}  # required, otherwise none
            status_mngr.update_status(new_status="Archived")

        assert returned_response_archived_ok["message"] in capsys.readouterr().out
