"""Custom Exception classes"""

# Standard library
import requests
import logging
import json

# Installed
import click

# Own modules
import dds_cli

# Logger
LOG = logging.getLogger(__name__)


class ConfigFileNotFoundError(click.ClickException):
    """The file containing user credentials not found."""

    def __init__(self, filepath, message: str = "Could not find the config file"):

        self.filepath = filepath
        self.message = message
        super().__init__(message)

    def __str__(self):
        return f"{self.message}: {self.filepath}"

    def show(self):
        click.echo(self)


class ConfigFileExtractionError(Exception):
    """Could not extract any info from the config file."""

    def __init__(
        self,
        filepath,
        message: str = "Could not extract info from config file",
        caught_exception=None,
    ):
        self.filepath = filepath
        self.message = message
        super().__init__(message)

        if caught_exception:
            LOG.exception(caught_exception.args[0] + "\n" + self.__str__())

    def __str__(self):
        return f"{self.message}: {self.filepath}"


class InvalidMethodError(Exception):
    """Valid methods are only ls, put, get, rm. Anything else should raise errors."""

    def __init__(self, attempted_method, message="Attempting an invalid method in the DDS"):
        self.method = attempted_method
        self.message = message
        super().__init__(message)

    def __str__(self):
        return f"{self.message}: {self.method}"


class DDSCLIException(click.ClickException):
    def __init__(self, message):
        super().__init__(message)


class AuthenticationError(click.ClickException):
    """Errors due to user authentication.

    Return the message with Rich no-entry-sign emoji either side.
    """

    def __init__(self, message, sign=":no_entry_sign:"):
        self.message = message
        self.sign = sign
        super().__init__(message)

    def __str__(self):
        return f"{self.sign} {self.message} {self.sign}"


class MissingCredentialsException(AuthenticationError):
    """All user options not specified"""

    def __init__(self, missing, message="Data Delivery System options are missing"):
        self.message = f"{message}: [red]{missing}[/red]"
        LOG.error(self.message)
        super().__init__(self.message)


class TokenNotFoundError(AuthenticationError):
    """No token retrieved from REST API"""

    def __init__(self, message, sign=":warning:"):
        LOG.error(message)
        super().__init__(message=message, sign=sign)


class ApiRequestError(requests.exceptions.RequestException):
    """Request to REST API failed."""

    def __init__(self, message):
        LOG.exception(message)
        super().__init__(message)


class ApiResponseError(Exception):
    """REST API Request does not return code 200 in response"""

    def __init__(self, message):
        LOG.exception(message)
        super().__init__(message)


class UploadError(Exception):
    """Errors relating to file uploads"""


class NoDataError(Exception):
    """Errors when there is no data to do anything with."""


class APIError(Exception):
    """Error connecting to the dds web server"""
