"""Tests for dds_cli.s3_connector."""

# IMPORTS ######################################################################
from unittest.mock import MagicMock, patch

from dds_cli.s3_connector import S3Connector


# HELPERS ######################################################################
def _create_connector():
    """Create S3Connector instance with mocked attributes."""
    # Bypass __post_init__ by creating instance without calling it
    # (__post_init__ requires API call)
    connector = S3Connector.__new__(S3Connector)

    # Manually set attributes that would normally be set by __post_init__
    connector.keys = {"access_key": "ACCESS", "secret_key": "SECRET"}
    connector.url = "https://s3.example.com"

    return connector


# TESTS ########################################################################
@patch("dds_cli.s3_connector.botocore.client.Config")  # --> mock_config_class
@patch("dds_cli.s3_connector.boto3.session.Session")  # --> mock_session_class
def test_connect_uses_custom_config(mock_session_class, mock_config_class):
    """Verify S3Connector.connect sets up boto3 session with custom config."""
    # Mock the session, resource and config
    mock_session = MagicMock()
    mock_resource = MagicMock()
    mock_config = MagicMock()

    # The actual session mock input should be mocked by the magic mock for the session
    mock_session.resource.return_value = mock_resource
    mock_session_class.return_value = mock_session

    # The actual config mock input should be mocked by the magic mock for the config
    mock_config_class.return_value = mock_config

    # Create connector and call the S3connector.connect method
    connector = _create_connector()
    result = connector.connect()

    # Verify that the config class was called with the expected timeout and retry values
    mock_config_class.assert_called_once_with(
        read_timeout=300, connect_timeout=60, retries={"max_attempts": 10}
    )

    # Verify that the session resource was called with the expected parameters and config
    mock_session.resource.assert_called_once_with(
        service_name="s3",
        endpoint_url="https://s3.example.com",
        aws_access_key_id="ACCESS",
        aws_secret_access_key="SECRET",
        config=mock_config,
    )

    # Verify that the returned resource is the mock resource and the config used is the mock config
    assert mock_session.resource.call_args.kwargs["config"] is mock_config
    assert result is mock_resource
