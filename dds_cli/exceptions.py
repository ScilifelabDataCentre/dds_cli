"""Custom Exception classes."""

# Standard library
import logging
import requests

# Installed
import click

# Own modules

# Logger
LOG = logging.getLogger(__name__)


class InvalidMethodError(Exception):
    """Valid methods are only ls, put, get, rm. Anything else should raise errors."""

    def __init__(self, attempted_method, message="Attempting an invalid method in the DDS"):
        """Init invalid method error."""
        self.method = attempted_method
        self.message = message
        super().__init__(message)

    def __str__(self):
        """Print message and attempted method."""
        return f"{self.message}: {self.method}"


class DDSCLIException(click.ClickException):
    """Base exception for click in DDS."""

    def __init__(self, message, sign=":warning-emoji:", show_emojis=False):
        """Init base exception."""
        self.message = message
        self.show_emojis = show_emojis
        self.sign = sign
        super().__init__(message)

    def __str__(self):
        """Format error message and return with signs."""
        msg = f"{self.sign} {self.message} {self.sign}" if self.show_emojis else self.message
        return msg


class AuthenticationError(click.ClickException):
    """Errors due to user authentication."""

    def __init__(self, message, sign=":no_entry_sign:"):
        """Update error message."""
        self.message = message
        self.sign = sign
        super().__init__(message)

    def __str__(self):
        """Return the message with Rich no-entry-sign emoji either side."""
        return f"{self.sign} {self.message} {self.sign}"


class TokenDeserializationError(Exception):
    """Error caused by being unable to deserialize the token."""

    def __init__(self, message):
        """Reformat error message."""
        super().__init__(message)


class TokenExpirationMissingError(Exception):
    """Error caused by missing token expiration time in the jose header of the token."""

    def __init__(self, message):
        """Reformat error message."""
        super().__init__(message)


class TokenNotFoundError(AuthenticationError):
    """No token retrieved from REST API or from File."""

    def __init__(self, message, sign=":warning-emoji:"):
        """Reformat error message."""
        super().__init__(message=message, sign=sign)


class ApiRequestError(requests.exceptions.RequestException):
    """Request to REST API failed."""

    def __init__(self, message):
        """Log and raise."""
        super().__init__(message)


class ApiResponseError(Exception):
    """REST API Request does not return code 200 in response."""

    def __init__(self, message):
        """Log and raise."""
        super().__init__(message)


class UploadError(Exception):
    """Errors relating to file uploads."""


class DownloadError(Exception):
    """Errors relating to file download."""


class NoDataError(Exception):
    """Errors when there is no data to do anything with."""


class APIError(Exception):
    """Error connecting to the dds web server."""


class NoKeyError(Exception):
    """Error when there's a missing key."""


class NoMOTDsError(Exception):
    """Error when there's no MOTDs to display."""

    def __init__(self, message):
        """Log and raise."""
        super().__init__(message)
