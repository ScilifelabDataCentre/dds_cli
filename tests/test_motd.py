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
        return runner(["motd", "add", ADD_JSON["message"]])

    yield _run


@pytest.fixture
def add_motd():
    """A fixture that mocks the requests.post method.

    The function returned by this fixture takes parameters that adjust the status_code,
    ok, and json message.
    """
    with unittest.mock.patch.object(requests, "post") as mock_motd:

        def _request_mock(status_code, message=None, ok=True):
            mock_returned_request = unittest.mock.MagicMock(status_code=status_code, ok=ok)
            mock_returned_request.json.return_value = {"message": message}
            mock_motd.return_value = mock_returned_request
            return mock_motd

        yield _request_mock


def test_add_motd_OK(runner_motd, add_motd):
    add_motd_OK = add_motd(200)
    result = runner_motd()

    assert result.exit_code == 0
    add_motd_OK.assert_called_with(
        dds_cli.DDSEndpoint.ADD_NEW_MOTD,
        json={**ADD_JSON},
        headers=unittest.mock.ANY,
        timeout=dds_cli.DDSEndpoint.TIMEOUT,
    )


def test_add_motd_fail(runner_motd, add_motd):
    add_motd_FAIL = add_motd(403, message="Passed message", ok=False)
    result = runner_motd()

    assert result.exit_code != 0
    assert "Only Super Admin can add a MOTD" in result.stderr
    assert "Passed message" in result.stderr
    add_motd_FAIL.assert_called_with(
        dds_cli.DDSEndpoint.ADD_NEW_MOTD,
        json={**ADD_JSON},
        headers=unittest.mock.ANY,
        timeout=dds_cli.DDSEndpoint.TIMEOUT,
    )
