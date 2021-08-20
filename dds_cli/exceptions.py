"""Custom Exception classes"""

# Standard library
import requests

# Installed
import click

# Own modules
import dds_cli


class ConfigFileNotFoundError(click.ClickException):
    """The file containing user credentials not found."""

    def __init__(self, filepath, message="Could not find the config file"):

        self.filepath = filepath
        self.message = message
        super().__init__(message)

    def __str__(self):
        return f"{self.message}: {self.filepath}"

    def show(self):
        click.echo(self)


class InvalidMethodError(Exception):
    """Valid methods are only ls, put, get, rm. Anything else should raise errors."""

    def __init__(self, attempted_method, message="Attempting an invalid method in the DDS"):
        self.method = attempted_method
        self.message = message
        super().__init__(message)

    def __str__(self):
        return f"{self.message}: {self.method}"


class AuthenticationError(Exception):
    """Errors due to user authentication.

    Return the message with Rich no-entry-sign emoji either side.
    """

    def __init__(self, message):
        self.message = message
        super().__init__(message)

    def __str__(self):
        return f":no_entry_sign: {self.message} :no_entry_sign:"


class MissingCredentialsException(AuthenticationError):
    """All user options not specified"""

    def __init__(self, missing, message="Data Delivery System options are missing"):

        self.message = f"{message}: {missing}"
        super().__init__(message)


class ApiRequestError(requests.exceptions.RequestException):
    """Request to REST API failed."""

    def __init__(self, message):
        super().__init__(message)


class UploadError(Exception):
    """Errors relating to file uploads"""


class NoDataError(Exception):
    """Errors when there is no data to do anything with."""


class APIError(Exception):
    """Error connecting to the dds web server"""
