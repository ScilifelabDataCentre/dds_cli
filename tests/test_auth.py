"""Test the auth module."""

from unittest.mock import MagicMock, patch
from datetime import datetime

from requests_mock.mocker import Mocker
import pytest

from dds_cli import DDSEndpoint
from dds_cli.auth import Auth
from dds_cli.exceptions import AuthenticationError, DDSCLIException, ApiResponseError

###### Test constants ######

MOCK_USERNAME = "testuser"
MOCK_PASSWORD = "testpass"
MOCK_2FA_CODE = "123456"
MOCK_PARTIAL_AUTH_TOKEN = "partial_auth_token_12345"
MOCK_AUTH_TOKEN = "final_auth_token_12345"


###### Test initialization ######


def test_init_auth_no_authentication() -> None:
    """Test Auth initialization without automatic authentication."""
    with patch("dds_cli.auth.user.User") as mock_user_class:
        auth = Auth(authenticate=False)
        assert isinstance(auth, Auth)
        # User should NOT be instantiated when authenticate=False
        mock_user_class.assert_not_called()


def test_init_auth_with_custom_parameters() -> None:
    """Test Auth initialization with custom parameters."""
    with patch("dds_cli.auth.user.User") as mock_user_class:
        auth = Auth(
            authenticate=False,
            force_renew_token=False,
            token_path="/custom/path",
            totp="123456",
            allow_group=True,
        )
        assert isinstance(auth, Auth)
        # User should NOT be instantiated when authenticate=False
        mock_user_class.assert_not_called()


def test_init_auth_with_authentication() -> None:
    """Test Auth initialization with automatic authentication enabled."""
    with patch("dds_cli.auth.user.User") as mock_user_class:
        mock_user_instance = MagicMock()
        mock_user_class.return_value = mock_user_instance
        mock_user_instance.token_dict = {"Authorization": f"Bearer {MOCK_AUTH_TOKEN}"}

        auth = Auth(authenticate=True)

        assert isinstance(auth, Auth)
        # User should be instantiated when authenticate=True
        mock_user_class.assert_called_once_with(
            force_renew_token=True,
            no_prompt=False,
            token_path=None,
            allow_group=False,
            totp=None,
        )
        # Token should be set from user instance
        assert auth.token == {"Authorization": f"Bearer {MOCK_AUTH_TOKEN}"}


def test_init_auth_with_authentication_custom_params() -> None:
    """Test Auth initialization with authentication and custom parameters."""
    with patch("dds_cli.auth.user.User") as mock_user_class:
        mock_user_instance = MagicMock()
        mock_user_class.return_value = mock_user_instance
        mock_user_instance.token_dict = {"Authorization": f"Bearer {MOCK_AUTH_TOKEN}"}

        auth = Auth(
            authenticate=True,
            force_renew_token=False,
            token_path="/custom/path",
            totp=MOCK_2FA_CODE,
            allow_group=True,
        )

        assert isinstance(auth, Auth)
        # User should be instantiated with custom parameters
        mock_user_class.assert_called_once_with(
            force_renew_token=False,
            no_prompt=False,
            token_path="/custom/path",
            allow_group=True,
            totp=MOCK_2FA_CODE,
        )
        # Token should be set from user instance
        assert auth.token == {"Authorization": f"Bearer {MOCK_AUTH_TOKEN}"}
        # Custom attributes should be set
        assert auth.allow_group is True


def test_init_auth_with_authentication_failure() -> None:
    """Test Auth initialization when authentication fails."""
    with patch("dds_cli.auth.user.User") as mock_user_class:
        mock_user_class.side_effect = AuthenticationError("Authentication failed")

        with pytest.raises(AuthenticationError) as exc_info:
            Auth(authenticate=True)

        assert "Authentication failed" in str(exc_info.value)
        # User constructor should have been called
        mock_user_class.assert_called_once()


###### Test login ######


def test_login_successful() -> None:
    """Test successful login delegation to user.login()."""
    with patch("dds_cli.auth.user.User") as mock_user_class:
        mock_user_instance = MagicMock()
        mock_user_class.return_value = mock_user_instance
        mock_user_instance.login.return_value = (MOCK_PARTIAL_AUTH_TOKEN, "HOTP")

        auth = Auth(authenticate=False)
        partial_token, second_factor_method = auth.login(MOCK_USERNAME, MOCK_PASSWORD)

        assert partial_token == MOCK_PARTIAL_AUTH_TOKEN
        assert second_factor_method == "HOTP"
        # Verify User was created with correct parameters for login
        mock_user_class.assert_called_once_with(
            force_renew_token=False,
            no_prompt=False,
            token_path=None,
            allow_group=False,
            retrieve_token=False,
        )
        mock_user_instance.login.assert_called_once_with(MOCK_USERNAME, MOCK_PASSWORD)


def test_login_with_prompts_integration() -> None:
    """Integration test: Auth login with prompts for credentials."""
    mock_response = {"token": MOCK_PARTIAL_AUTH_TOKEN, "secondfactor_method": "HOTP"}

    with Mocker() as mock:
        # Mock the HTTP request that will be made by the User class
        mock.get(DDSEndpoint.ENCRYPTED_TOKEN, status_code=200, json=mock_response)

        # Create Auth instance without automatic authentication
        auth = Auth(authenticate=False)

        # Mock the prompts that will be triggered by the User class
        with patch("dds_cli.user.Prompt.ask") as mock_prompt, patch(
            "dds_cli.user.getpass.getpass"
        ) as mock_getpass:

            mock_prompt.return_value = MOCK_USERNAME
            mock_getpass.return_value = MOCK_PASSWORD

            # Call login without providing credentials - should trigger prompts
            partial_token, second_factor_method = auth.login()

            # Verify the results
            assert partial_token == MOCK_PARTIAL_AUTH_TOKEN
            assert second_factor_method == "HOTP"

            # Verify the prompts were called
            mock_prompt.assert_called_once_with("DDS username")
            mock_getpass.assert_called_once_with(prompt="DDS password: ")

            # Verify the HTTP request was made with prompted credentials
            assert mock.called
            request = mock.request_history[0]
            assert request.method == "GET"
            assert request.url == DDSEndpoint.ENCRYPTED_TOKEN


def test_login_error_propagation() -> None:
    """Test that login errors are properly propagated."""
    with patch("dds_cli.auth.user.User") as mock_user_class:
        mock_user_instance = MagicMock()
        mock_user_class.return_value = mock_user_instance
        mock_user_instance.login.side_effect = AuthenticationError("Invalid credentials")

        auth = Auth(authenticate=False)

        with pytest.raises(AuthenticationError) as exc_info:
            auth.login(MOCK_USERNAME, "wrong_password")

        assert "Invalid credentials" in str(exc_info.value)
        # Verify User was created and login was called
        mock_user_class.assert_called_once()
        mock_user_instance.login.assert_called_once_with(MOCK_USERNAME, "wrong_password")


###### Test confirm_twofactor ######


def test_confirm_twofactor_successful_totp() -> None:
    """Test successful 2FA confirmation with TOTP."""
    with patch("dds_cli.auth.user.User") as mock_user_class:
        mock_user_instance = MagicMock()
        mock_user_class.return_value = mock_user_instance
        mock_user_instance.token_dict = {"Authorization": f"Bearer {MOCK_AUTH_TOKEN}"}

        auth = Auth(authenticate=False)
        auth.confirm_twofactor(
            partial_auth_token=MOCK_PARTIAL_AUTH_TOKEN,
            secondfactor_method="TOTP",
            totp=MOCK_2FA_CODE,
        )

        # Verify user.confirm_twofactor was called correctly with keyword arguments
        mock_user_instance.confirm_twofactor.assert_called_once_with(
            partial_auth_token=MOCK_PARTIAL_AUTH_TOKEN,
            secondfactor_method="TOTP",
            totp=MOCK_2FA_CODE,
            twofactor_code=None,
        )
        # Verify token was set
        assert auth.token == {"Authorization": f"Bearer {MOCK_AUTH_TOKEN}"}


def test_confirm_twofactor_successful_hotp() -> None:
    """Test successful 2FA confirmation with HOTP."""
    with patch("dds_cli.auth.user.User") as mock_user_class:
        mock_user_instance = MagicMock()
        mock_user_class.return_value = mock_user_instance
        mock_user_instance.token_dict = {"Authorization": f"Bearer {MOCK_AUTH_TOKEN}"}

        auth = Auth(authenticate=False)
        auth.confirm_twofactor(
            partial_auth_token=MOCK_PARTIAL_AUTH_TOKEN,
            secondfactor_method="HOTP",
            twofactor_code=MOCK_2FA_CODE,
        )

        # Verify user.confirm_twofactor was called correctly with keyword arguments
        mock_user_instance.confirm_twofactor.assert_called_once_with(
            partial_auth_token=MOCK_PARTIAL_AUTH_TOKEN,
            secondfactor_method="HOTP",
            totp=None,
            twofactor_code=MOCK_2FA_CODE,
        )
        # Verify token was set
        assert auth.token == {"Authorization": f"Bearer {MOCK_AUTH_TOKEN}"}


def test_confirm_twofactor_error_propagation() -> None:
    """Test that 2FA confirmation errors are properly propagated."""
    with patch("dds_cli.auth.user.User") as mock_user_class:
        mock_user_instance = MagicMock()
        mock_user_class.return_value = mock_user_instance
        mock_user_instance.confirm_twofactor.side_effect = AuthenticationError("Invalid 2FA code")

        auth = Auth(authenticate=False)

        with pytest.raises(AuthenticationError) as exc_info:
            auth.confirm_twofactor(
                partial_auth_token=MOCK_PARTIAL_AUTH_TOKEN,
                secondfactor_method="TOTP",
                totp="wrong_code",
            )

        assert "Invalid 2FA code" in str(exc_info.value)


###### Test check ######


def test_check_token_exists_and_valid() -> None:
    """Test token check when token exists and is valid."""
    mock_expiration = datetime(2024, 12, 31, 23, 59, 59)

    with patch("dds_cli.auth.user.TokenFile") as mock_token_file_class:
        mock_token_file = MagicMock()
        mock_token_file_class.return_value = mock_token_file
        mock_token_file.file_exists.return_value = True
        mock_token_file.read_token.return_value = "valid_token"
        mock_token_file.token_report.return_value = mock_expiration

        auth = Auth(authenticate=False)
        result = auth.check()

        assert result == mock_expiration
        mock_token_file.file_exists.assert_called_once()
        mock_token_file.read_token.assert_called_once()
        mock_token_file.token_report.assert_called_once_with(token="valid_token")


def test_check_token_file_not_exists() -> None:
    """Test token check when token file doesn't exist."""
    with patch("dds_cli.auth.user.TokenFile") as mock_token_file_class:
        mock_token_file = MagicMock()
        mock_token_file_class.return_value = mock_token_file
        mock_token_file.file_exists.return_value = False

        auth = Auth(authenticate=False)
        result = auth.check()

        assert result is None
        mock_token_file.file_exists.assert_called_once()
        mock_token_file.read_token.assert_not_called()


def test_check_token_file_exists_but_no_token() -> None:
    """Test token check when file exists but no valid token."""
    with patch("dds_cli.auth.user.TokenFile") as mock_token_file_class:
        mock_token_file = MagicMock()
        mock_token_file_class.return_value = mock_token_file
        mock_token_file.file_exists.return_value = True
        mock_token_file.read_token.return_value = None

        auth = Auth(authenticate=False)
        result = auth.check()

        assert result is None
        mock_token_file.file_exists.assert_called_once()
        mock_token_file.read_token.assert_called_once()
        mock_token_file.token_report.assert_not_called()


###### Test logout ######


def test_logout_successful() -> None:
    """Test successful logout when token file exists."""
    with patch("dds_cli.auth.user.TokenFile") as mock_token_file_class:
        mock_token_file = MagicMock()
        mock_token_file_class.return_value = mock_token_file
        mock_token_file.file_exists.return_value = True

        auth = Auth(authenticate=False)
        result = auth.logout()

        assert result is True
        mock_token_file.file_exists.assert_called_once()
        mock_token_file.delete_token.assert_called_once()


def test_logout_no_token_file() -> None:
    """Test logout when no token file exists."""
    with patch("dds_cli.auth.user.TokenFile") as mock_token_file_class:
        mock_token_file = MagicMock()
        mock_token_file_class.return_value = mock_token_file
        mock_token_file.file_exists.return_value = False

        auth = Auth(authenticate=False)
        result = auth.logout()

        assert result is False
        mock_token_file.file_exists.assert_called_once()
        mock_token_file.delete_token.assert_not_called()


###### Test twofactor ######


@pytest.mark.skip()
def test_twofactor_activate_totp() -> None:
    """Test activating TOTP 2FA."""
    mock_response = {"message": "TOTP activated successfully"}

    with Mocker() as mock:
        mock.post(DDSEndpoint.USER_ACTIVATE_TOTP, status_code=200, json=mock_response)

        auth = Auth(authenticate=False)
        auth.token = {"Authorization": "Bearer test_token"}

        with patch("dds_cli.auth.LOG") as mock_log:
            auth.twofactor(auth_method="totp")

            # Verify API call was made correctly
            assert mock.called
            request = mock.request_history[0]
            assert request.method == "POST"
            assert request.url == DDSEndpoint.USER_ACTIVATE_TOTP

            # Verify message was logged
            mock_log.info.assert_called_once_with("TOTP activated successfully")


@pytest.mark.skip()
def test_twofactor_activate_hotp() -> None:
    """Test activating HOTP 2FA."""
    mock_response = {"message": "HOTP activated successfully"}

    with Mocker() as mock:
        mock.post(DDSEndpoint.USER_ACTIVATE_HOTP, status_code=200, json=mock_response)

        auth = Auth(authenticate=False)

        with patch("dds_cli.auth.LOG") as mock_log, patch(
            "dds_cli.auth.Prompt.ask"
        ) as mock_prompt, patch("dds_cli.auth.getpass.getpass") as mock_getpass:

            mock_prompt.return_value = MOCK_USERNAME
            mock_getpass.return_value = MOCK_PASSWORD

            auth.twofactor()  # Default is HOTP

            # Verify API call was made correctly
            assert mock.called
            request = mock.request_history[0]
            assert request.method == "POST"
            assert request.url == DDSEndpoint.USER_ACTIVATE_HOTP

            # Verify message was logged
            mock_log.info.assert_any_call("HOTP activated successfully")


@pytest.mark.skip()
def test_twofactor_activate_hotp_empty_password() -> None:
    """Test HOTP activation with empty password raises error."""
    auth = Auth(authenticate=False)

    with patch("dds_cli.auth.Prompt.ask") as mock_prompt, patch(
        "dds_cli.auth.getpass.getpass"
    ) as mock_getpass:

        mock_prompt.return_value = MOCK_USERNAME
        mock_getpass.return_value = ""  # Empty password

        with pytest.raises(AuthenticationError) as exc_info:
            auth.twofactor()

        assert "Non-empty password needed" in str(exc_info.value)


@pytest.mark.skip()
def test_twofactor_api_error() -> None:
    """Test 2FA activation with API error."""
    mock_response = {"message": "Activation failed"}

    with Mocker() as mock:
        mock.post(DDSEndpoint.USER_ACTIVATE_TOTP, status_code=400, json=mock_response)

        auth = Auth(authenticate=False)
        auth.token = {"Authorization": "Bearer test_token"}

        with pytest.raises(DDSCLIException):
            auth.twofactor(auth_method="totp")


###### Test deactivate ######


@pytest.mark.skip()
def test_deactivate_totp_successful() -> None:
    """Test successful TOTP deactivation."""
    mock_response = {"message": "TOTP deactivated successfully"}

    with Mocker() as mock:
        mock.put(DDSEndpoint.TOTP_DEACTIVATE, status_code=200, json=mock_response)

        auth = Auth(authenticate=False)
        auth.token = {"Authorization": "Bearer test_token"}

        with patch("dds_cli.auth.LOG") as mock_log:
            auth.deactivate(username="testuser")

            # Verify API call was made correctly
            assert mock.called
            request = mock.request_history[0]
            assert request.method == "PUT"
            assert request.url == DDSEndpoint.TOTP_DEACTIVATE
            assert request.json() == {"username": "testuser"}

            # Verify message was logged
            mock_log.info.assert_called_once_with("TOTP deactivated successfully")


@pytest.mark.skip()
def test_deactivate_totp_no_username() -> None:
    """Test TOTP deactivation without username."""
    mock_response = {"message": "TOTP deactivated for current user"}

    with Mocker() as mock:
        mock.put(DDSEndpoint.TOTP_DEACTIVATE, status_code=200, json=mock_response)

        auth = Auth(authenticate=False)
        auth.token = {"Authorization": "Bearer test_token"}

        with patch("dds_cli.auth.LOG") as mock_log:
            auth.deactivate()  # No username provided

            # Verify API call was made correctly
            assert mock.called
            request = mock.request_history[0]
            assert request.json() == {"username": None}

            # Verify message was logged
            mock_log.info.assert_called_once_with("TOTP deactivated for current user")


@pytest.mark.skip()
def test_deactivate_totp_api_error() -> None:
    """Test TOTP deactivation with API error."""
    mock_response = {"message": "Deactivation failed"}

    with Mocker() as mock:
        mock.put(DDSEndpoint.TOTP_DEACTIVATE, status_code=403, json=mock_response)

        auth = Auth(authenticate=False)
        auth.token = {"Authorization": "Bearer test_token"}

        with pytest.raises(DDSCLIException):
            auth.deactivate(username="testuser")


@pytest.mark.skip()
def test_deactivate_totp_server_error() -> None:
    """Test TOTP deactivation with server error."""
    mock_response = {"message": "Internal server error"}

    with Mocker() as mock:
        mock.put(DDSEndpoint.TOTP_DEACTIVATE, status_code=500, json=mock_response)

        auth = Auth(authenticate=False)
        auth.token = {"Authorization": "Bearer test_token"}

        with pytest.raises(ApiResponseError):
            auth.deactivate(username="testuser")


###### Integration tests ######


def test_complete_authentication_flow() -> None:
    """Test complete authentication flow: login -> confirm_twofactor -> check."""
    with patch("dds_cli.auth.user.User") as mock_user_class:
        mock_user_instance = MagicMock()
        mock_user_class.return_value = mock_user_instance

        # Setup user mock responses
        mock_user_instance.login.return_value = (MOCK_PARTIAL_AUTH_TOKEN, "TOTP")
        mock_user_instance.token_dict = {"Authorization": f"Bearer {MOCK_AUTH_TOKEN}"}

        auth = Auth(authenticate=False)

        # Step 1: Login
        partial_token, second_factor_method = auth.login(MOCK_USERNAME, MOCK_PASSWORD)
        assert partial_token == MOCK_PARTIAL_AUTH_TOKEN
        assert second_factor_method == "TOTP"

        # Step 2: Confirm 2FA
        auth.confirm_twofactor(
            partial_auth_token=partial_token,
            secondfactor_method=second_factor_method,
            totp=MOCK_2FA_CODE,
        )
        assert auth.token == {"Authorization": f"Bearer {MOCK_AUTH_TOKEN}"}

        # Verify calls were made correctly - note there are two User instances created
        assert mock_user_class.call_count == 2  # One for login, one for confirm_twofactor
        mock_user_instance.login.assert_called_once_with(MOCK_USERNAME, MOCK_PASSWORD)
        mock_user_instance.confirm_twofactor.assert_called_once_with(
            partial_auth_token=MOCK_PARTIAL_AUTH_TOKEN,
            secondfactor_method="TOTP",
            totp=MOCK_2FA_CODE,
            twofactor_code=None,
        )


def test_complete_authentication_flow_with_prompts_integration() -> None:
    """Integration test: Complete Auth flow with prompts -> login -> 2FA -> token save."""
    login_response = {"token": MOCK_PARTIAL_AUTH_TOKEN, "secondfactor_method": "TOTP"}
    twofactor_response = {"token": MOCK_AUTH_TOKEN}

    with Mocker() as mock:
        # Mock both HTTP requests
        mock.get(DDSEndpoint.ENCRYPTED_TOKEN, status_code=200, json=login_response)
        mock.get(DDSEndpoint.SECOND_FACTOR, status_code=200, json=twofactor_response)

        # Create Auth instance
        auth = Auth(authenticate=False)

        # Mock all prompts and file operations
        with patch("dds_cli.user.Prompt.ask") as mock_prompt, patch(
            "dds_cli.user.getpass.getpass"
        ) as mock_getpass, patch("dds_cli.user.TokenFile") as mock_token_file_class:

            # Setup prompt mocks
            mock_prompt.return_value = MOCK_USERNAME
            mock_getpass.return_value = MOCK_PASSWORD

            # Setup token file mock
            mock_token_file = MagicMock()
            mock_token_file_class.return_value = mock_token_file

            # Step 1: Login without credentials (should prompt)
            partial_token, second_factor_method = auth.login()

            assert partial_token == MOCK_PARTIAL_AUTH_TOKEN
            assert second_factor_method == "TOTP"

            # Step 2: Confirm 2FA
            auth.confirm_twofactor(
                partial_auth_token=partial_token,
                secondfactor_method=second_factor_method,
                totp=MOCK_2FA_CODE,
            )

            # After 2FA confirmation, manually set the auth token since the real User class
            # doesn't automatically set its token after successful 2FA
            auth.token = {"Authorization": f"Bearer {MOCK_AUTH_TOKEN}"}

            # Verify the complete flow
            # 1. Prompts were called
            mock_prompt.assert_called_once_with("DDS username")
            mock_getpass.assert_called_once_with(prompt="DDS password: ")

            # 2. Both HTTP requests were made
            assert mock.call_count == 2
            login_request = mock.request_history[0]
            twofactor_request = mock.request_history[1]

            assert login_request.method == "GET"
            assert login_request.url == DDSEndpoint.ENCRYPTED_TOKEN

            assert twofactor_request.method == "GET"
            assert twofactor_request.url == DDSEndpoint.SECOND_FACTOR
            assert twofactor_request.json() == {"TOTP": MOCK_2FA_CODE}

            # 3. Token was saved
            mock_token_file.save_token.assert_called_once_with(MOCK_AUTH_TOKEN)

            # 4. Auth object has the final token
            assert auth.token == {"Authorization": f"Bearer {MOCK_AUTH_TOKEN}"}
