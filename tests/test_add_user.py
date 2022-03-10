# Standard library
import unittest.mock

# Installed
import pytest
import requests

# Own modules
import dds_cli

ADD_JSON = {"email": "test.testsson@example.com", "role": "Researcher", "unit": None}
PROJECT = {"project": "test_project"}


@pytest.fixture
def runner_with_project(runner):
    """Run dds add-user with a project specified."""

    def _run():
        return runner(
            [
                "user",
                "add",
                "-r",
                ADD_JSON["role"],
                "-p",
                PROJECT["project"],
                "--no-mail",
                ADD_JSON["email"],
            ]
        )

    yield _run


@pytest.fixture
def runner_no_project(runner):
    """Run dds add-user without a project specified."""

    def _run():
        return runner(["user", "add", "-r", ADD_JSON["role"], ADD_JSON["email"]])

    yield _run


@pytest.fixture
def add_user():
    """A fixture that mocks the requests.post method.

    The functioned returned by this fixture takes parameters that adjust the status_code,
    ok, and json message.
    """
    with unittest.mock.patch.object(requests, "post") as mock_B:

        def _request_mock(status_code, message=None, ok=True):
            mock_returned_request = unittest.mock.MagicMock(status_code=status_code, ok=ok)
            mock_returned_request.json.return_value = {"message": message}
            mock_B.return_value = mock_returned_request
            return mock_B

        yield _request_mock


def test_add_user_no_project_OK(runner_no_project, add_user):
    add_user_OK = add_user(200)
    result = runner_no_project()
    add_user_OK.assert_called_with(
        dds_cli.DDSEndpoint.USER_ADD,
        json={**ADD_JSON, "send_email": True},
        params={"project": None},
        headers=unittest.mock.ANY,
        timeout=dds_cli.DDSEndpoint.TIMEOUT,
    )

    assert result.exit_code == 0


def test_add_user_no_project_fail(runner_no_project, add_user):
    add_user_FAIL = add_user(403, message="Specifically passed message", ok=False)
    result = runner_no_project()
    add_user_FAIL.assert_called_with(
        dds_cli.DDSEndpoint.USER_ADD,
        json={**ADD_JSON, "send_email": True},
        params={"project": None},
        headers=unittest.mock.ANY,
        timeout=dds_cli.DDSEndpoint.TIMEOUT,
    )

    assert "Could not add user" in result.stderr
    assert "Specifically passed message" in result.stderr
    assert result.exit_code != 0


def test_add_user_with_project_ok(runner_with_project, add_user):
    add_user_OK = add_user(200)
    result = runner_with_project()
    add_user_OK.assert_called_with(
        dds_cli.DDSEndpoint.USER_ADD,
        json={**ADD_JSON, "send_email": False},
        params=PROJECT,
        headers=unittest.mock.ANY,
        timeout=dds_cli.DDSEndpoint.TIMEOUT,
    )

    assert result.exit_code == 0


def test_add_user_with_project_fail(runner_with_project, add_user):
    add_user_OK = add_user(403, message="Specifically passed message", ok=False)
    result = runner_with_project()
    add_user_OK.assert_called_with(
        dds_cli.DDSEndpoint.USER_ADD,
        json={**ADD_JSON, "send_email": False},
        params=PROJECT,
        headers=unittest.mock.ANY,
        timeout=dds_cli.DDSEndpoint.TIMEOUT,
    )

    assert "Could not add user" in result.stderr
    assert "Specifically passed message" in result.stderr
    assert result.exit_code != 0
