"""Test the base module authentication functionality."""

from unittest.mock import MagicMock, patch

import pytest

from dds_cli.base import DDSBaseClass
from dds_cli.exceptions import AuthenticationError

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
