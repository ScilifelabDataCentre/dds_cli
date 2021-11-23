# Standard library
from unittest.mock import patch, MagicMock

# Installed
from click.testing import CliRunner
import requests
from dds_cli import DDSEndpoint

# Own modules
from dds_cli.__main__ import dds_main
import dds_cli
from dds_cli.user import User


@patch.object(requests, "post")
@patch.object(User, "_User__retrieve_token")
def test_add_user_no_project(mock_A, mock_B):
    mock_A.return_value = None
    mock_returned_request = MagicMock(status_code=200)
    mock_returned_request.json.return_value = {}
    mock_B.return_value = mock_returned_request

    runner = CliRunner(mix_stderr=False)
    add_user_email = "test.testsson@example.com"
    add_user_role = "Researcher"
    result = runner.invoke(
        dds_main,
        ["add-user", "-u", "unituser", "-e", add_user_email, "-r", add_user_role],
        catch_exceptions=False,
    )

    mock_B.assert_called()
    print(result.stderr)
    assert result.exit_code == 0
