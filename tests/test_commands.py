"""Test the commands."""

#### Very incomplete suite #####

from click.testing import CliRunner
from unittest.mock import MagicMock, patch
import pytest


import dds_cli.exceptions
from dds_cli import dds_main


### PARAMETERIZED options to pass to tests ###
@pytest.mark.parametrize(
    "user_choice, expected_auth_method, expected_exit_code",
    [
        ("Email", "hotp", 0),
        ("Authenticator App", "totp", 0),
        ("Cancel", None, 0),  # Cancel exits with 0
    ],
)

#### AUTH COMMANDS #####

# TWOFACTOR ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ TWOFACTOR #


def test_configure_choices(user_choice, expected_auth_method, expected_exit_code):
    runner = CliRunner()
    with patch(
        questionary.select, "auth_method_choice", return_value=user_choice
    ) as mock_select, patch("dds_cli.auth.Auth") as mock_auth:

        # Mock the Auth context manager
        mock_auth_instance = MagicMock()
        mock_auth.return_value.__enter__.return_value = mock_auth_instance

        result = runner.invoke(dds_main, ["auth", "twofactor", "configure"])

        assert result.exit_code == expected_exit_code

        if user_choice == "Cancel":
            # No call to twofactor
            mock_auth_instance.twofactor.assert_not_called()
        else:
            mock_auth_instance.twofactor.assert_called_once_with(auth_method=expected_auth_method)
