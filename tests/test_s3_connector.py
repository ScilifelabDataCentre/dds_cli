"""Tests for dds_cli.s3_connector."""

# IMPORTS ######################################################################
import logging
from unittest.mock import MagicMock, patch

import pytest
from boto3.exceptions import Boto3Error
from botocore.exceptions import BotoCoreError

from dds_cli import constants
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
        read_timeout=constants.READ_TIMEOUT,
        connect_timeout=constants.CONNECT_TIMEOUT,
        retries={"max_attempts": 10},
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


@patch("dds_cli.s3_connector.boto3.session.Session.resource")
def test_connect_logs_success(mock_resource_method, caplog):
    """Verify successful connection returns resource and logs debug message."""

    # Mock resource and set the actual method to return it when called in test
    mock_res = MagicMock()
    mock_resource_method.return_value = mock_res

    # Create connector
    connector = _create_connector()

    with caplog.at_level(logging.DEBUG):
        # Attempt to connect to S3
        result = connector.connect()

    # Verify that the connector returns a mocked resource and that the correct message is logged
    assert result is mock_res
    assert "Connected to S3." in caplog.messages


# Set up the boto3 resource to raise an exception
# parameterize to test multiple exception classes
@pytest.mark.parametrize("exc_cls", [BotoCoreError, Boto3Error])
def test_connect_logs_warning_and_raises(exc_cls, caplog):
    """Verify that S3Connector.connect propagates errors and logs a warning."""
    # Create connector
    connector = _create_connector()

    with patch(
        "dds_cli.s3_connector.boto3.session.Session.resource",
        side_effect=exc_cls(),
    ):
        with caplog.at_level(logging.WARNING):
            # Attempt to connect
            with pytest.raises(exc_cls):
                connector.connect()

    # Verify that the correct warning was logged
    assert any(
        record.levelno == logging.WARNING and "S3 connection failed" in record.message
        for record in caplog.records
    )
