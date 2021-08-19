"""Custom Exception classes"""

import click


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


class AuthenticationError(Exception):
    """Errors due to user authentication.

    Return the message with Rich no-entry-sign emoji either side.
    """

    def __str__(self):
        return f":no_entry_sign: {self.args[0]} :no_entry_sign:"


class UploadError(Exception):
    """Errors relating to file uploads"""


class NoDataError(Exception):
    """Errors when there is no data to do anything with."""


class APIError(Exception):
    """Error connecting to the dds web server"""
