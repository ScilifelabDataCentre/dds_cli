# Standard library
import unittest.mock

# Installed
import click.testing
import pytest
import requests


# Own modules
from dds_cli.__main__ import dds_main
from dds_cli import DDSEndpoint
import dds_cli
from dds_cli.user import User

ADD_JSON = {"email": "test.testsson@example.com", "role": "Researcher"}


@pytest.fixture
def runner():
    runner = click.testing.CliRunner(mix_stderr=False)
    yield runner


@pytest.fixture
def retrieve_token():
    with unittest.mock.patch.object(User, "_User__retrieve_token") as mock_A:
        mock_A.return_value = None
        yield mock_A


@pytest.fixture
def add_user():
    with unittest.mock.patch.object(requests, "post") as mock_B:
        mock_returned_request = unittest.mock.MagicMock(status_code=200)
        mock_returned_request.json.return_value = {}
        mock_B.return_value = mock_returned_request
        yield mock_B


def test_add_user_no_project_OK(runner, retrieve_token, add_user):
    result = runner.invoke(
        dds_main,
        ["add-user", "-u", "unituser", "-e", ADD_JSON["email"], "-r", ADD_JSON["role"]],
        catch_exceptions=False,
    )

    add_user.assert_called_with(DDSEndpoint.USER_ADD, json=ADD_JSON, headers=unittest.mock.ANY)

    assert result.exit_code == 0


@unittest.mock.patch.object(requests, "post")
@unittest.mock.patch.object(User, "_User__retrieve_token")
def test_add_user_no_project_fail(mock_A, mock_B):
    mock_A.return_value = None
    mock_returned_request = unittest.mock.MagicMock(status_code=403, ok=False)
    mock_returned_request.json.return_value = {"message": "Specificly passed message"}
    mock_B.return_value = mock_returned_request
    runner = click.testing.CliRunner(mix_stderr=False)

    result = runner.invoke(
        dds_main,
        ["add-user", "-u", "unituser", "-e", ADD_JSON["email"], "-r", ADD_JSON["role"]],
        catch_exceptions=False,
    )

    mock_B.assert_called_with(DDSEndpoint.USER_ADD, json=ADD_JSON, headers=unittest.mock.ANY)

    assert "Could not add user" in result.stderr
    assert "Specificly passed message" in result.stderr
    assert result.exit_code != 0
