"""Test the base module authentication functionality."""

from unittest.mock import MagicMock, patch

import pytest

from dds_cli.base import DDSBaseClass
from dds_cli.exceptions import AuthenticationError, NoKeyError
from dds_cli import DDS_KEYS_REQUIRED_METHODS

###### Test constants ######

MOCK_USERNAME = "testuser"
MOCK_PASSWORD = "testpass"
MOCK_2FA_CODE = "123456"
MOCK_PARTIAL_AUTH_TOKEN = "partial_auth_token_12345"
MOCK_AUTH_TOKEN = "final_auth_token_12345"
MOCK_TOKEN_DICT = {"Authorization": f"Bearer {MOCK_AUTH_TOKEN}"}
MOCK_PROJECT = "test_project_123"


###### Test initialization without authentication ######


def test_init_base_class_no_authentication():
    """Test DDSBaseClass initialization without authentication."""
    base = DDSBaseClass(authenticate=False)

    assert isinstance(base, DDSBaseClass)
    assert base.project is None
    assert base.method is None
    assert base.no_prompt is False
    assert base.token_path is None
    assert base.totp is None
    assert base.stop_doing is False


def test_init_base_class_with_parameters_no_authentication():
    """Test DDSBaseClass initialization with custom parameters but no authentication."""
    base = DDSBaseClass(
        project=MOCK_PROJECT,
        method="list",
        authenticate=False,
        no_prompt=True,
        token_path="/custom/token/path",
        totp=MOCK_2FA_CODE,
        allow_group=True,
    )

    assert base.project == MOCK_PROJECT
    assert base.method == "list"
    assert base.no_prompt is True
    assert base.token_path == "/custom/token/path"
    assert base.totp == MOCK_2FA_CODE


###### Test initialization with authentication ######


@patch("dds_cli.base.user.User")
def test_init_base_class_with_authentication_default_params(mock_user_class):
    """Test DDSBaseClass initialization with authentication using default parameters."""
    # Setup mock user
    mock_user_instance = MagicMock()
    mock_user_class.return_value = mock_user_instance
    mock_user_instance.login.return_value = (MOCK_PARTIAL_AUTH_TOKEN, "TOTP")
    mock_user_instance.token_dict = MOCK_TOKEN_DICT

    base = DDSBaseClass(authenticate=True)

    # Verify User was created with default parameters
    mock_user_class.assert_called_once_with(
        force_renew_token=False,
        no_prompt=False,
        token_path=None,
        allow_group=False,
    )

    # Verify authentication flow was executed
    mock_user_instance.login.assert_called_once()
    mock_user_instance.confirm_twofactor.assert_called_once_with(
        MOCK_PARTIAL_AUTH_TOKEN, "TOTP", totp=None
    )

    # Verify token was set
    assert base.token == MOCK_TOKEN_DICT


@patch("dds_cli.base.user.User")
def test_init_base_class_with_authentication_custom_params(mock_user_class):
    """Test DDSBaseClass initialization with authentication using custom parameters."""
    # Setup mock user
    mock_user_instance = MagicMock()
    mock_user_class.return_value = mock_user_instance
    mock_user_instance.login.return_value = (MOCK_PARTIAL_AUTH_TOKEN, "HOTP")
    mock_user_instance.token_dict = MOCK_TOKEN_DICT

    base = DDSBaseClass(
        authenticate=True,
        force_renew_token=True,
        no_prompt=True,
        token_path="/custom/path",
        allow_group=True,
        totp=MOCK_2FA_CODE,
    )

    # Verify User was created with custom parameters
    mock_user_class.assert_called_once_with(
        force_renew_token=True,
        no_prompt=True,
        token_path="/custom/path",
        allow_group=True,
    )

    # Verify authentication flow was executed with TOTP
    mock_user_instance.login.assert_called_once()
    mock_user_instance.confirm_twofactor.assert_called_once_with(
        MOCK_PARTIAL_AUTH_TOKEN, "HOTP", totp=MOCK_2FA_CODE
    )

    # Verify token was set
    assert base.token == MOCK_TOKEN_DICT


@patch("dds_cli.base.user.User")
def test_init_base_class_authentication_totp_method(mock_user_class):
    """Test DDSBaseClass authentication with TOTP method."""
    # Setup mock user
    mock_user_instance = MagicMock()
    mock_user_class.return_value = mock_user_instance
    mock_user_instance.login.return_value = (MOCK_PARTIAL_AUTH_TOKEN, "TOTP")
    mock_user_instance.token_dict = MOCK_TOKEN_DICT

    base = DDSBaseClass(authenticate=True, totp=MOCK_2FA_CODE)

    # Verify TOTP was passed to confirm_twofactor
    mock_user_instance.confirm_twofactor.assert_called_once_with(
        MOCK_PARTIAL_AUTH_TOKEN, "TOTP", totp=MOCK_2FA_CODE
    )

    assert base.token == MOCK_TOKEN_DICT


@patch("dds_cli.base.user.User")
def test_init_base_class_authentication_hotp_method(mock_user_class):
    """Test DDSBaseClass authentication with HOTP method."""
    # Setup mock user
    mock_user_instance = MagicMock()
    mock_user_class.return_value = mock_user_instance
    mock_user_instance.login.return_value = (MOCK_PARTIAL_AUTH_TOKEN, "HOTP")
    mock_user_instance.token_dict = MOCK_TOKEN_DICT

    base = DDSBaseClass(authenticate=True)

    # Verify HOTP method was handled correctly (no TOTP code)
    mock_user_instance.confirm_twofactor.assert_called_once_with(
        MOCK_PARTIAL_AUTH_TOKEN, "HOTP", totp=None
    )

    assert base.token == MOCK_TOKEN_DICT


###### Test authentication error scenarios ######


@patch("dds_cli.base.user.User")
def test_init_base_class_login_failure(mock_user_class):
    """Test DDSBaseClass initialization when login fails."""
    # Setup mock user to raise authentication error
    mock_user_instance = MagicMock()
    mock_user_class.return_value = mock_user_instance
    mock_user_instance.login.side_effect = AuthenticationError("Invalid credentials")

    with pytest.raises(AuthenticationError) as exc_info:
        DDSBaseClass(authenticate=True)

    assert "Invalid credentials" in str(exc_info.value)

    # Verify login was called but confirm_twofactor was not
    mock_user_instance.login.assert_called_once()
    mock_user_instance.confirm_twofactor.assert_not_called()


@patch("dds_cli.base.user.User")
def test_init_base_class_twofactor_failure(mock_user_class):
    """Test DDSBaseClass initialization when two-factor authentication fails."""
    # Setup mock user
    mock_user_instance = MagicMock()
    mock_user_class.return_value = mock_user_instance
    mock_user_instance.login.return_value = (MOCK_PARTIAL_AUTH_TOKEN, "TOTP")
    mock_user_instance.confirm_twofactor.side_effect = AuthenticationError("Invalid 2FA code")

    with pytest.raises(AuthenticationError) as exc_info:
        DDSBaseClass(authenticate=True, totp="wrong_code")

    assert "Invalid 2FA code" in str(exc_info.value)

    # Verify both login and confirm_twofactor were called
    mock_user_instance.login.assert_called_once()
    mock_user_instance.confirm_twofactor.assert_called_once_with(
        MOCK_PARTIAL_AUTH_TOKEN, "TOTP", totp="wrong_code"
    )


###### Test initialization with DDS keys required methods ######


@patch("dds_cli.base.user.User")
@patch("dds_cli.base.s3.S3Connector")
@patch("dds_cli.base.dds_cli.utils.perform_request")
def test_init_base_class_with_put_method(mock_perform_request, mock_s3_connector, mock_user_class):
    """Test DDSBaseClass initialization with 'put' method (requires keys and S3)."""
    # Setup mock user
    mock_user_instance = MagicMock()
    mock_user_class.return_value = mock_user_instance
    mock_user_instance.login.return_value = (MOCK_PARTIAL_AUTH_TOKEN, "TOTP")
    mock_user_instance.token_dict = MOCK_TOKEN_DICT

    # Setup mock S3 connector
    mock_s3_instance = MagicMock()
    mock_s3_connector.return_value = mock_s3_instance

    # Setup mock API responses for keys
    mock_perform_request.side_effect = [
        ({"public": "mock_public_key"}, None),  # Public key response
    ]

    # Setup mock staging directory
    mock_staging_dir = MagicMock()
    mock_staging_dir.directories = {"ROOT": "/tmp/staging", "LOGS": "/tmp/logs"}

    base = DDSBaseClass(
        project=MOCK_PROJECT, method="put", authenticate=True, staging_dir=mock_staging_dir
    )

    # Verify authentication occurred
    assert base.token == MOCK_TOKEN_DICT

    # Verify S3 connector was created for put method
    mock_s3_connector.assert_called_once_with(project_id=MOCK_PROJECT, token=MOCK_TOKEN_DICT)
    assert base.s3connector == mock_s3_instance

    # Verify project keys were retrieved (only public for put)
    assert mock_perform_request.call_count == 1
    assert base.keys[0] is None  # private key
    assert base.keys[1] == "mock_public_key"  # public key

    # Verify staging directory and other attributes
    assert base.dds_directory == mock_staging_dir
    assert base.temporary_directory == "/tmp/staging"


@patch("dds_cli.base.user.User")
@patch("dds_cli.base.dds_cli.utils.perform_request")
def test_init_base_class_with_get_method(mock_perform_request, mock_user_class):
    """Test DDSBaseClass initialization with 'get' method (requires both keys)."""
    # Setup mock user
    mock_user_instance = MagicMock()
    mock_user_class.return_value = mock_user_instance
    mock_user_instance.login.return_value = (MOCK_PARTIAL_AUTH_TOKEN, "TOTP")
    mock_user_instance.token_dict = MOCK_TOKEN_DICT

    # Setup mock API responses for keys
    mock_perform_request.side_effect = [
        ({"public": "mock_public_key"}, None),  # Public key response
        ({"private": "mock_private_key"}, None),  # Private key response
    ]

    # Setup mock staging directory
    mock_staging_dir = MagicMock()
    mock_staging_dir.directories = {"ROOT": "/tmp/staging", "LOGS": "/tmp/logs"}

    base = DDSBaseClass(
        project=MOCK_PROJECT, method="get", authenticate=True, staging_dir=mock_staging_dir
    )

    # Verify authentication occurred
    assert base.token == MOCK_TOKEN_DICT

    # Verify project keys were retrieved (both private and public for get)
    assert mock_perform_request.call_count == 2
    assert base.keys[0] == "mock_private_key"  # private key
    assert base.keys[1] == "mock_public_key"  # public key

    # Verify no S3 connector for get method
    assert not hasattr(base, "s3connector")


@patch("dds_cli.base.user.User")
@patch("dds_cli.base.s3.S3Connector")
@patch("dds_cli.base.dds_cli.utils.perform_request")
def test_init_base_class_key_retrieval_failure(
    mock_perform_request, mock_s3_connector, mock_user_class
):
    """Test DDSBaseClass initialization when key retrieval fails."""
    # Setup mock user
    mock_user_instance = MagicMock()
    mock_user_class.return_value = mock_user_instance
    mock_user_instance.login.return_value = (MOCK_PARTIAL_AUTH_TOKEN, "TOTP")
    mock_user_instance.token_dict = MOCK_TOKEN_DICT

    # Setup mock S3 connector
    mock_s3_instance = MagicMock()
    mock_s3_connector.return_value = mock_s3_instance

    # Setup mock API response without public key
    mock_perform_request.return_value = ({}, None)  # Missing public key

    # Setup mock staging directory
    mock_staging_dir = MagicMock()
    mock_staging_dir.directories = {"ROOT": "/tmp/staging", "LOGS": "/tmp/logs"}

    with pytest.raises(NoKeyError) as exc_info:
        DDSBaseClass(
            project=MOCK_PROJECT, method="put", authenticate=True, staging_dir=mock_staging_dir
        )

    assert "Project access denied: No public key" in str(exc_info.value)


###### Test method parameter validation ######


def test_init_base_class_dds_keys_required_methods():
    """Test that DDS_KEYS_REQUIRED_METHODS contains expected methods."""
    # This test ensures we're testing the right methods
    assert "put" in DDS_KEYS_REQUIRED_METHODS
    assert "get" in DDS_KEYS_REQUIRED_METHODS


@patch("dds_cli.base.user.User")
def test_init_base_class_method_not_requiring_keys(mock_user_class):
    """Test DDSBaseClass initialization with method that doesn't require keys."""
    # Setup mock user
    mock_user_instance = MagicMock()
    mock_user_class.return_value = mock_user_instance
    mock_user_instance.login.return_value = (MOCK_PARTIAL_AUTH_TOKEN, "TOTP")
    mock_user_instance.token_dict = MOCK_TOKEN_DICT

    base = DDSBaseClass(
        project=MOCK_PROJECT,
        method="list",  # Method not in DDS_KEYS_REQUIRED_METHODS
        authenticate=True,
    )

    # Verify authentication occurred
    assert base.token == MOCK_TOKEN_DICT

    # Verify no keys or staging directory setup
    assert not hasattr(base, "keys")
    assert not hasattr(base, "dds_directory")
    assert not hasattr(base, "s3connector")


###### Test context manager behavior ######


@patch("dds_cli.base.user.User")
def test_base_class_context_manager_enter(mock_user_class):
    """Test DDSBaseClass as context manager - __enter__ method."""
    # Setup mock user
    mock_user_instance = MagicMock()
    mock_user_class.return_value = mock_user_instance
    mock_user_instance.login.return_value = (MOCK_PARTIAL_AUTH_TOKEN, "TOTP")
    mock_user_instance.token_dict = MOCK_TOKEN_DICT

    base = DDSBaseClass(authenticate=True)

    # Test context manager enter
    context_base = base.__enter__()
    assert context_base is base


@patch("dds_cli.base.user.User")
@patch("dds_cli.base.dds_cli.utils.perform_request")
def test_base_class_context_manager_exit_no_exception(mock_perform_request, mock_user_class):
    """Test DDSBaseClass as context manager - __exit__ with no exception."""
    # Setup mock user
    mock_user_instance = MagicMock()
    mock_user_class.return_value = mock_user_instance
    mock_user_instance.login.return_value = (MOCK_PARTIAL_AUTH_TOKEN, "TOTP")
    mock_user_instance.token_dict = MOCK_TOKEN_DICT

    # Setup mock API responses for keys (get method needs both private and public)
    mock_perform_request.side_effect = [
        ({"public": "mock_public_key"}, None),  # Public key response
        ({"private": "mock_private_key"}, None),  # Private key response
    ]

    # Setup mock staging directory for get method
    mock_staging_dir = MagicMock()
    mock_staging_dir.directories = {"ROOT": "/tmp/staging", "LOGS": "/tmp/logs"}

    with patch(
        "dds_cli.base.DDSBaseClass._DDSBaseClass__printout_delivery_summary"
    ) as mock_summary:
        base = DDSBaseClass(
            authenticate=True, method="get", project=MOCK_PROJECT, staging_dir=mock_staging_dir
        )  # Use get method to test summary

        # Test context manager exit with no exception
        result = base.__exit__(None, None, None)

        assert result is True
        mock_summary.assert_called_once()


@patch("dds_cli.base.user.User")
def test_base_class_context_manager_exit_with_exception(mock_user_class):
    """Test DDSBaseClass as context manager - __exit__ with exception."""
    # Setup mock user
    mock_user_instance = MagicMock()
    mock_user_class.return_value = mock_user_instance
    mock_user_instance.login.return_value = (MOCK_PARTIAL_AUTH_TOKEN, "TOTP")
    mock_user_instance.token_dict = MOCK_TOKEN_DICT

    base = DDSBaseClass(authenticate=True, method="list")  # Use list method to avoid keys setup

    # Test context manager exit with exception
    result = base.__exit__(ValueError, ValueError("test error"), None)

    assert result is False  # Exception not handled


###### Integration tests ######


@patch("dds_cli.base.user.User")
def test_complete_authentication_flow_integration(mock_user_class):
    """Test complete authentication flow integration."""
    # Setup mock user with realistic behavior
    mock_user_instance = MagicMock()
    mock_user_class.return_value = mock_user_instance
    mock_user_instance.login.return_value = (MOCK_PARTIAL_AUTH_TOKEN, "TOTP")
    mock_user_instance.token_dict = MOCK_TOKEN_DICT

    # Test complete flow
    base = DDSBaseClass(
        project=MOCK_PROJECT,
        method="list",
        authenticate=True,
        force_renew_token=True,
        no_prompt=True,
        token_path="/custom/path",
        allow_group=True,
        totp=MOCK_2FA_CODE,
    )

    # Verify all parameters were passed correctly
    mock_user_class.assert_called_once_with(
        force_renew_token=True,
        no_prompt=True,
        token_path="/custom/path",
        allow_group=True,
    )

    # Verify authentication flow completed
    mock_user_instance.login.assert_called_once()
    mock_user_instance.confirm_twofactor.assert_called_once_with(
        MOCK_PARTIAL_AUTH_TOKEN, "TOTP", totp=MOCK_2FA_CODE
    )

    # Verify final state
    assert base.token == MOCK_TOKEN_DICT
    assert base.project == MOCK_PROJECT
    assert base.method == "list"
    assert base.no_prompt is True
    assert base.token_path == "/custom/path"
    assert base.totp == MOCK_2FA_CODE
    assert base.stop_doing is False
