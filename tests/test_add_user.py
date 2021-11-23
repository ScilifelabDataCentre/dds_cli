# Standard library
import unittest.mock

# Installed
import click.testing
import pytest
import requests


# Own modules
import dds_cli
from dds_cli.__main__ import dds_main
from dds_cli.user import User

ADD_JSON = {"email": "test.testsson@example.com", "role": "Researcher"}


@pytest.fixture
def retrieve_token():
    """A fixture to mock authentication by having a None token for every user"""
    with unittest.mock.patch.object(User, "_User__retrieve_token") as mock_A:
        mock_A.return_value = None
        yield mock_A


@pytest.fixture
def runner(retrieve_token):
    """A fixture that returns the click cli runner. The runner is invoked
    when the function returned by this fixture is called."""
    runner = click.testing.CliRunner(mix_stderr=False)

    def _run():
        return runner.invoke(
            dds_main,
            ["add-user", "-u", "unituser", "-e", ADD_JSON["email"], "-r", ADD_JSON["role"]],
            catch_exceptions=False,
        )

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


def test_add_user_no_project_OK(runner, add_user):
    add_user_OK = add_user(200)
    result = runner()
    add_user_OK.assert_called_with(
        dds_cli.DDSEndpoint.USER_ADD, json=ADD_JSON, headers=unittest.mock.ANY
    )

    assert result.exit_code == 0


def test_add_user_no_project_fail(runner, add_user):
    add_user_FAIL = add_user(403, message="Specifically passed message", ok=False)
    result = runner()
    add_user_FAIL.assert_called_with(
        dds_cli.DDSEndpoint.USER_ADD, json=ADD_JSON, headers=unittest.mock.ANY
    )

    assert "Could not add user" in result.stderr
    assert "Specifically passed message" in result.stderr
    assert result.exit_code != 0
