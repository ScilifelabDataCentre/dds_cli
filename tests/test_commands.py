"""Tests for CLI commands in dds_cli.__main__"""

from click.testing import CliRunner
from unittest.mock import MagicMock, patch
import pytest


import dds_cli.exceptions
from dds_cli.__main__ import dds_main


#### AUTH COMMANDS #####

## TWOFACTOR subcommands ##


# parametrized options to pass to the test
@pytest.mark.parametrize(
    "user_choice, expected_auth_method, expected_exit_code",
    [
        ("Email", "hotp", 0),
        ("Authenticator App", "totp", 0),
        ("Cancel", None, 0),  # Cancel exits with 0
    ],
)
def test_auth_configure_ok(user_choice, expected_auth_method, expected_exit_code):
    """Test of configure two factor method - ok"""

    runner = CliRunner()
    with patch("dds_cli.__main__.questionary.select") as mock_select, patch(
        "dds_cli.auth.Auth"
    ) as mock_auth:

        # Mock the user selecting option
        mock_select.return_value.ask.return_value = user_choice

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


# parametrized options to pass to the test
@pytest.mark.parametrize("user_choice", ["Email", "Authenticator App"])
@pytest.mark.parametrize(
    "exc_type", [dds_cli.exceptions.DDSCLIException, dds_cli.exceptions.ApiResponseError]
)
def test_auth_configure_exceptions(exc_type, user_choice):
    """Test of configure two factor - fails with exceptions"""

    runner = CliRunner()
    with patch("dds_cli.__main__.questionary.select") as mock_select, patch(
        "dds_cli.auth.Auth"
    ) as mock_auth:

        # Mock the user selecting option
        mock_select.return_value.ask.return_value = user_choice

        # Mock Auth context manager to raise exception
        mock_auth_instance = MagicMock()
        mock_auth.return_value.__enter__.return_value = mock_auth_instance
        mock_auth_instance.twofactor.side_effect = exc_type("error")

        result = runner.invoke(dds_main, ["auth", "twofactor", "configure"])

        assert result.exit_code == 1
        assert "error" in result.output


#### USER COMMANDS #####

## Activate and deactivate users ##


@pytest.mark.parametrize("confirm", [True, False])
def test_user_activate_confirm_ok(confirm):
    """Test user activation when confirmation is yes/no. - no errors"""

    runner = CliRunner()
    with patch(
        "dds_cli.__main__.rich.prompt.Confirm.ask", return_value=confirm
    ) as mock_confirm, patch("dds_cli.account_manager.AccountManager") as mock_manager:

        mock_manager_instance = MagicMock()
        mock_manager.return_value.__enter__.return_value = mock_manager_instance

        result = runner.invoke(dds_main, ["user", "activate", "someone@example.org"])

        assert result.exit_code == 0
        mock_confirm.assert_called_once()

        if confirm:
            mock_manager_instance.user_activation.assert_called_once_with(
                email="someone@example.org", action="reactivate"
            )
        else:
            mock_manager_instance.user_activation.assert_not_called()


@pytest.mark.parametrize("confirm", [True, False])
def test_user_deactivate_confirm_ok(confirm):
    """Test user deactivation when confirmation is yes/no. - no errors"""

    runner = CliRunner()
    with patch(
        "dds_cli.__main__.rich.prompt.Confirm.ask", return_value=confirm
    ) as mock_confirm, patch("dds_cli.account_manager.AccountManager") as mock_manager:

        mock_manager_instance = MagicMock()
        mock_manager.return_value.__enter__.return_value = mock_manager_instance

        result = runner.invoke(dds_main, ["user", "deactivate", "someone@example.org"])

        assert result.exit_code == 0
        mock_confirm.assert_called_once()

        if confirm:
            mock_manager_instance.user_activation.assert_called_once_with(
                email="someone@example.org", action="deactivate"
            )
        else:
            mock_manager_instance.user_activation.assert_not_called()


@pytest.mark.parametrize(
    "exc_type",
    [
        dds_cli.exceptions.AuthenticationError,
        dds_cli.exceptions.ApiResponseError,
        dds_cli.exceptions.ApiRequestError,
        dds_cli.exceptions.DDSCLIException,
    ],
)
def test_user_activate_exceptions(exc_type):
    """Test user activation when AccountManager raises errors."""

    runner = CliRunner()
    with patch("dds_cli.__main__.rich.prompt.Confirm.ask", return_value=True), patch(
        "dds_cli.account_manager.AccountManager"
    ) as mock_manager:

        mock_manager_instance = MagicMock()
        mock_manager_instance.user_activation.side_effect = exc_type("error")
        mock_manager.return_value.__enter__.return_value = mock_manager_instance

        result = runner.invoke(dds_main, ["user", "activate", "someone@example.org"])

        assert result.exit_code == 1
        assert "error" in result.output


@pytest.mark.parametrize(
    "exc_type",
    [
        dds_cli.exceptions.AuthenticationError,
        dds_cli.exceptions.ApiResponseError,
        dds_cli.exceptions.ApiRequestError,
        dds_cli.exceptions.DDSCLIException,
    ],
)
def test_user_deactivate_exceptions(exc_type):
    """Test user deactivation when AccountManager raises errors."""

    runner = CliRunner()
    with patch("dds_cli.__main__.rich.prompt.Confirm.ask", return_value=True), patch(
        "dds_cli.account_manager.AccountManager"
    ) as mock_manager:

        mock_manager_instance = MagicMock()
        mock_manager_instance.user_activation.side_effect = exc_type("error")
        mock_manager.return_value.__enter__.return_value = mock_manager_instance

        result = runner.invoke(dds_main, ["user", "deactivate", "someone@example.org"])

        assert result.exit_code == 1
        assert "error" in result.output
