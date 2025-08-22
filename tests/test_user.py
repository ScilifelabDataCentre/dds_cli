"""Test the user module."""

from unittest.mock import MagicMock, patch

import pytest
from requests_mock.mocker import Mocker

from dds_cli import DDSEndpoint
from dds_cli.user import User
from dds_cli.exceptions import (
    DDSCLIException,
    AuthenticationError,
    ApiRequestError,
    ApiResponseError,
)

###### Test constants ######

MOCK_USERNAME = "test_user"
MOCK_PASSWORD = "test_password"
MOCK_2FA_CODE = "123456"

MOCK_PARTIAL_AUTH_TOKEN = "partial_auth_token_12345"
MOCK_AUTH_TOKEN = "auth_token_12345"


###### Test initialization ######


def test_init_user() -> None:
    """Test the initialization of the user module."""
    user = User(force_renew_token=False, no_prompt=True, retrieve_token=False)
    assert isinstance(user, User)


def test_user_token_dict() -> None:
    """Test the token dictionary of the user."""
    user = User(force_renew_token=False, no_prompt=True, retrieve_token=False)
    assert user.token_dict == {"Authorization": f"Bearer {user.token}"}


###### Test login ######


def test_login_successful_hotp() -> None:
    """Test successful login with valid credentials."""
    mock_response = {"token": MOCK_PARTIAL_AUTH_TOKEN, "secondfactor_method": "HOTP"}

    with Mocker() as mock:
        mock.get(DDSEndpoint.ENCRYPTED_TOKEN, status_code=200, json=mock_response)

        user = User(force_renew_token=False, no_prompt=True, retrieve_token=False)

        partial_token, second_factor_method = user.login(MOCK_USERNAME, MOCK_PASSWORD)

        assert partial_token == MOCK_PARTIAL_AUTH_TOKEN
        assert second_factor_method == "HOTP"


def test_login_successful_totp() -> None:
    """Test successful login with TOTP second factor method."""
    mock_response = {"token": MOCK_PARTIAL_AUTH_TOKEN, "secondfactor_method": "TOTP"}

    with Mocker() as mock:
        mock.get(DDSEndpoint.ENCRYPTED_TOKEN, status_code=200, json=mock_response)

        user = User(force_renew_token=False, no_prompt=True, retrieve_token=False)
        partial_token, second_factor_method = user.login(MOCK_USERNAME, MOCK_PASSWORD)

        assert partial_token == MOCK_PARTIAL_AUTH_TOKEN
        assert second_factor_method == "TOTP"


def test_login_successful_with_prompts() -> None:
    """Test successful login when credentials are prompted for."""
    mock_response = {"token": MOCK_PARTIAL_AUTH_TOKEN, "secondfactor_method": "HOTP"}

    with Mocker() as mock:
        mock.get(DDSEndpoint.ENCRYPTED_TOKEN, status_code=200, json=mock_response)

        # Create user that allows prompting (no_prompt=False) but doesn't auto-retrieve token
        user = User(force_renew_token=False, no_prompt=False, retrieve_token=False)

        # Mock both username and password prompts
        with pytest.MonkeyPatch().context() as mp:
            # Mock the username prompt
            mp.setattr("dds_cli.user.Prompt.ask", lambda prompt: MOCK_USERNAME)
            # Mock the password prompt
            mp.setattr("dds_cli.user.getpass.getpass", lambda prompt: MOCK_PASSWORD)

            # Call login without providing credentials - should prompt
            partial_token, second_factor_method = user.login()

            assert partial_token == MOCK_PARTIAL_AUTH_TOKEN
            assert second_factor_method == "HOTP"

            # Verify the HTTP request was made with the prompted credentials
            assert mock.called
            request = mock.request_history[0]
            assert request.method == "GET"
            assert request.url == DDSEndpoint.ENCRYPTED_TOKEN


def test_login_prompts_called_correctly() -> None:
    """Test that login prompts are called with correct messages."""
    mock_response = {"token": MOCK_PARTIAL_AUTH_TOKEN, "secondfactor_method": "TOTP"}

    with Mocker() as mock:
        mock.get(DDSEndpoint.ENCRYPTED_TOKEN, status_code=200, json=mock_response)

        user = User(force_renew_token=False, no_prompt=False, retrieve_token=False)

        # Use MagicMock to track the calls
        with pytest.MonkeyPatch().context() as mp:
            mock_prompt = MagicMock(return_value=MOCK_USERNAME)
            mock_getpass = MagicMock(return_value=MOCK_PASSWORD)

            mp.setattr("dds_cli.user.Prompt.ask", mock_prompt)
            mp.setattr("dds_cli.user.getpass.getpass", mock_getpass)

            user.login()  # No credentials provided

            # Verify prompts were called with correct messages
            mock_prompt.assert_called_once_with("DDS username")
            mock_getpass.assert_called_once_with(prompt="DDS password: ")


def test_login_invalid_credentials() -> None:
    """Test login with invalid credentials returns 401."""
    mock_response = {"message": "Missing or incorrect credentials"}

    with Mocker() as mock:
        mock.get(DDSEndpoint.ENCRYPTED_TOKEN, status_code=401, json=mock_response)

        user = User(force_renew_token=False, no_prompt=True, retrieve_token=False)

        with pytest.raises(DDSCLIException) as exc_info:
            user.login("wrong_user", "wrong_password")

        assert "Failed to authenticate user" in str(exc_info.value)


def test_login_empty_username() -> None:
    """Test that login raises error with empty username."""
    user = User(force_renew_token=False, no_prompt=True, retrieve_token=False)

    with pytest.raises(AuthenticationError) as exc_info:
        user.login("", MOCK_PASSWORD)

    assert "Non-empty username needed to be able to authenticate" in str(exc_info.value)


def test_login_empty_password() -> None:
    """Test that login raises error with empty password."""
    user = User(force_renew_token=False, no_prompt=True, retrieve_token=False)

    with pytest.raises(AuthenticationError) as exc_info:
        user.login(MOCK_USERNAME, "")

    assert "Non-empty password needed to be able to authenticate" in str(exc_info.value)


def test_login_unicode_error() -> None:
    """Test handling of unicode characters in credentials."""
    user = User(force_renew_token=False, no_prompt=True, retrieve_token=False)

    with Mocker() as mock:
        # Mock the request to raise UnicodeEncodeError
        mock.get(
            DDSEndpoint.ENCRYPTED_TOKEN,
            exc=UnicodeEncodeError("ascii", "test©user", 4, 5, "ordinal not in range(128)"),
        )

        with pytest.raises(ApiRequestError) as exc_info:
            user.login("test©user", MOCK_PASSWORD)

        assert "The entered username or password seems to contain invalid characters" in str(
            exc_info.value
        )


def test_login_server_error() -> None:
    """Test handling of server errors (500)."""
    mock_response = {"message": "Internal server error"}

    with Mocker() as mock:
        mock.get(DDSEndpoint.ENCRYPTED_TOKEN, status_code=500, json=mock_response)

        user = User(force_renew_token=False, no_prompt=True, retrieve_token=False)

        with pytest.raises(ApiResponseError) as exc_info:
            user.login(MOCK_USERNAME, MOCK_PASSWORD)

        # Should still raise an error for server issues
        assert "Failed to authenticate user" in str(exc_info.value)


# NOTE: Should it be able to handle none as token?
@pytest.mark.skip()
def test_login_missing_token_in_response() -> None:
    """Test handling when API doesn't return token."""
    mock_response = {"secondfactor_method": "HOTP"}  # Missing token

    with Mocker() as mock:
        mock.get(DDSEndpoint.ENCRYPTED_TOKEN, status_code=200, json=mock_response)

        user = User(force_renew_token=False, no_prompt=True, retrieve_token=False)
        partial_token, second_factor_method = user.login(MOCK_USERNAME, MOCK_PASSWORD)

        assert partial_token is None
        assert second_factor_method == "HOTP"


# NOTE: Should it be able to handle none as secondfactor_method?
@pytest.mark.skip()
def test_login_missing_secondfactor_in_response() -> None:
    """Test handling when API doesn't return secondfactor_method."""
    mock_response = {"token": MOCK_PARTIAL_AUTH_TOKEN}  # Missing secondfactor_method

    with Mocker() as mock:
        mock.get(DDSEndpoint.ENCRYPTED_TOKEN, status_code=200, json=mock_response)

        user = User(force_renew_token=False, no_prompt=True, retrieve_token=False)
        partial_token, second_factor_method = user.login(MOCK_USERNAME, MOCK_PASSWORD)

        assert partial_token == MOCK_PARTIAL_AUTH_TOKEN
        assert second_factor_method is None


@pytest.mark.skip()
def test_login_network_error() -> None:
    """Test handling of network connectivity issues."""
    with Mocker() as mock:
        # Mock network error
        mock.get(DDSEndpoint.ENCRYPTED_TOKEN, exc=ConnectionError("Network unreachable"))

        user = User(force_renew_token=False, no_prompt=True, retrieve_token=False)

        # The mocked ConnectionError will be raised directly
        with pytest.raises(ConnectionError) as exc_info:
            user.login(MOCK_USERNAME, MOCK_PASSWORD)

        assert "Network unreachable" in str(exc_info.value)


def test_login_no_prompt_without_credentials() -> None:
    """Test that login raises error when no_prompt=True and no credentials provided."""
    user = User(force_renew_token=False, no_prompt=True, retrieve_token=False)

    with pytest.raises(AuthenticationError) as exc_info:
        user.login()  # No username/password provided

    assert "Authentication not possible when running with --no-prompt" in str(exc_info.value)


###### Test confirm_twofactor ######


def test_confirm_twofactor_successful_totp_with_totp_param() -> None:
    """Test successful 2FA confirmation using TOTP with totp parameter."""
    mock_response = {"token": MOCK_AUTH_TOKEN}

    with Mocker() as mock:
        mock.get(DDSEndpoint.SECOND_FACTOR, status_code=200, json=mock_response)

        user = User(force_renew_token=False, no_prompt=True, retrieve_token=False)

        # Mock token file operations to avoid file system interactions
        with pytest.MonkeyPatch().context() as mp:
            mock_token_file = MagicMock()
            mp.setattr("dds_cli.user.TokenFile", lambda **kwargs: mock_token_file)

            user.confirm_twofactor(
                partial_auth_token=MOCK_PARTIAL_AUTH_TOKEN,
                secondfactor_method="TOTP",
                totp=MOCK_2FA_CODE,
            )

            # Verify token was saved
            mock_token_file.save_token.assert_called_once_with(MOCK_AUTH_TOKEN)


def test_confirm_twofactor_successful_hotp_with_twofactor_code() -> None:
    """Test successful 2FA confirmation using HOTP with twofactor_code parameter."""
    mock_response = {"token": MOCK_AUTH_TOKEN}

    with Mocker() as mock:
        mock.get(DDSEndpoint.SECOND_FACTOR, status_code=200, json=mock_response)

        user = User(force_renew_token=False, no_prompt=True, retrieve_token=False)

        with pytest.MonkeyPatch().context() as mp:
            mock_token_file = MagicMock()
            mp.setattr("dds_cli.user.TokenFile", lambda **kwargs: mock_token_file)

            user.confirm_twofactor(
                partial_auth_token=MOCK_PARTIAL_AUTH_TOKEN,
                secondfactor_method="HOTP",
                twofactor_code=MOCK_2FA_CODE,
            )

            # Verify the request was made correctly
            assert mock.called
            request = mock.request_history[0]
            assert request.json() == {"HOTP": MOCK_2FA_CODE}

            # Verify token was saved
            mock_token_file.save_token.assert_called_once_with(MOCK_AUTH_TOKEN)


def test_confirm_twofactor_successful_totp_with_twofactor_code() -> None:
    """Test successful 2FA confirmation using TOTP with twofactor_code parameter."""
    mock_response = {"token": MOCK_AUTH_TOKEN}

    with Mocker() as mock:
        mock.get(DDSEndpoint.SECOND_FACTOR, status_code=200, json=mock_response)

        user = User(force_renew_token=False, no_prompt=True, retrieve_token=False)

        with pytest.MonkeyPatch().context() as mp:
            mock_token_file = MagicMock()
            mp.setattr("dds_cli.user.TokenFile", lambda **kwargs: mock_token_file)

            user.confirm_twofactor(
                partial_auth_token=MOCK_PARTIAL_AUTH_TOKEN,
                secondfactor_method="TOTP",
                twofactor_code=MOCK_2FA_CODE,
            )

            # Verify token was saved
            mock_token_file.save_token.assert_called_once_with(MOCK_AUTH_TOKEN)


def test_confirm_twofactor_totp_not_enabled_error() -> None:
    """Test that TOTP code raises error when TOTP is not enabled."""
    user = User(force_renew_token=False, no_prompt=True, retrieve_token=False)

    with pytest.raises(AuthenticationError) as exc_info:
        user.confirm_twofactor(
            partial_auth_token=MOCK_PARTIAL_AUTH_TOKEN,
            secondfactor_method="HOTP",  # HOTP but trying to use TOTP
            totp=MOCK_2FA_CODE,
        )

    assert "you have not yet activated one-time authentication codes from authenticator app" in str(
        exc_info.value
    )


def test_confirm_twofactor_invalid_code() -> None:
    """Test handling of invalid 2FA codes."""
    mock_response = {"message": "Invalid authentication code"}

    with Mocker() as mock:
        mock.get(DDSEndpoint.SECOND_FACTOR, status_code=401, json=mock_response)

        user = User(force_renew_token=False, no_prompt=True, retrieve_token=False)

        with pytest.raises(DDSCLIException) as exc_info:
            user.confirm_twofactor(
                partial_auth_token=MOCK_PARTIAL_AUTH_TOKEN,
                secondfactor_method="TOTP",
                totp="wrong_code",
            )

        assert "Failed to authenticate with one-time authentication code" in str(exc_info.value)


def test_confirm_twofactor_missing_token_in_response() -> None:
    """Test handling when API doesn't return final token."""
    mock_response = {"message": "Success"}  # Missing token

    with Mocker() as mock:
        mock.get(DDSEndpoint.SECOND_FACTOR, status_code=200, json=mock_response)

        user = User(force_renew_token=False, no_prompt=True, retrieve_token=False)

        with pytest.raises(AuthenticationError) as exc_info:
            user.confirm_twofactor(
                partial_auth_token=MOCK_PARTIAL_AUTH_TOKEN,
                secondfactor_method="TOTP",
                totp=MOCK_2FA_CODE,
            )

        assert "Missing token in authentication response" in str(exc_info.value)


def test_confirm_twofactor_server_error() -> None:
    """Test handling of server errors during 2FA confirmation."""
    mock_response = {"message": "Internal server error"}

    with Mocker() as mock:
        mock.get(DDSEndpoint.SECOND_FACTOR, status_code=500, json=mock_response)

        user = User(force_renew_token=False, no_prompt=True, retrieve_token=False)

        with pytest.raises(ApiResponseError) as exc_info:
            user.confirm_twofactor(
                partial_auth_token=MOCK_PARTIAL_AUTH_TOKEN,
                secondfactor_method="HOTP",
                twofactor_code=MOCK_2FA_CODE,
            )

        assert "Failed to authenticate with second factor" in str(exc_info.value)


@pytest.mark.skip()
def test_confirm_twofactor_network_error() -> None:
    """Test handling of network errors during 2FA confirmation."""
    with Mocker() as mock:
        mock.get(DDSEndpoint.SECOND_FACTOR, exc=ConnectionError("Network unreachable"))

        user = User(force_renew_token=False, no_prompt=True, retrieve_token=False)

        with pytest.raises(ConnectionError) as exc_info:
            user.confirm_twofactor(
                partial_auth_token=MOCK_PARTIAL_AUTH_TOKEN,
                secondfactor_method="TOTP",
                totp=MOCK_2FA_CODE,
            )

        assert "Network unreachable" in str(exc_info.value)


def test_confirm_twofactor_expired_partial_token() -> None:
    """Test handling of expired partial auth token."""
    mock_response = {"message": "Token expired"}

    with Mocker() as mock:
        mock.get(DDSEndpoint.SECOND_FACTOR, status_code=401, json=mock_response)

        user = User(force_renew_token=False, no_prompt=True, retrieve_token=False)

        with pytest.raises(DDSCLIException) as exc_info:
            user.confirm_twofactor(
                partial_auth_token="expired_token",
                secondfactor_method="TOTP",
                totp=MOCK_2FA_CODE,
            )

        # Should raise error about authentication failure
        assert "Failed to authenticate with one-time authentication code" in str(exc_info.value)


def test_confirm_twofactor_partial_token_authorization_header() -> None:
    """Test that partial token is correctly used in authorization header."""
    mock_response = {"token": "final_token"}

    with Mocker() as mock:
        mock.get(DDSEndpoint.SECOND_FACTOR, status_code=200, json=mock_response)

        user = User(force_renew_token=False, no_prompt=True, retrieve_token=False)

        with pytest.MonkeyPatch().context() as mp:
            mock_token_file = MagicMock()
            mp.setattr("dds_cli.user.TokenFile", lambda **kwargs: mock_token_file)

            test_partial_token = "test_partial_token_xyz"
            user.confirm_twofactor(
                partial_auth_token=test_partial_token,
                secondfactor_method="HOTP",
                twofactor_code=MOCK_2FA_CODE,
            )

            # Verify authorization header contains the partial token
            request = mock.request_history[0]
            assert request.headers["Authorization"] == f"Bearer {test_partial_token}"
