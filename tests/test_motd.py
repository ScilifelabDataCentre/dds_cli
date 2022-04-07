# Standard library
import unittest.mock

# Installed
import pytest
import requests

# Own modules
import dds_cli

ADD_JSON = {"message": "Test MOTD"}


@pytest.fixture
def runner_motd(runner):
    """Run dds motd add."""

    def _run():
        return runner(["motd", "add", "-m", ADD_JSON["message"]])

    yield _run


@pytest.fixture
def add_motd():
    """A fixture that mocks the requests.post method.

    The function returned by this fixture takes parameters that adjust the status_code,
    ok, and json message.
    """
    with unittest.mock.patch.object(requests, "post") as mock_motd:

        def _request_mock(status_code, message=None, ok=True):
            #ToDo
            mock_returned_request = unittest.mock.MagicMock(status_code=status_code, ok=ok)
            mock_returned_request.json.return_value = {"message": message}
            mock_motd.return_value = mock_returned_request
            return mock_motd

        yield _request_mock


def test_add_motd_OK(runner_motd, add_motd):
    add_user_OK = add_motd(200)
    result = runner_motd()
    add_user_OK.assert_called_with(
        dds_cli.DDSEndpoint.USER_ADD,
        json={**ADD_JSON, "send_email": True},
        params={"project": None},
        headers=unittest.mock.ANY,
        timeout=dds_cli.DDSEndpoint.TIMEOUT,
    )

    assert result.exit_code == 0