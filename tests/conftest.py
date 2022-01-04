# Standard library
import unittest.mock

# Installed
import click.testing
import pytest

# Own modules
from dds_cli.user import User
from dds_cli.__main__ import dds_main


@pytest.fixture
def retrieve_token():
    """Fixture to mock authentication by having a None token for every user."""
    with unittest.mock.patch.object(User, "_User__retrieve_token") as mock_A:
        mock_A.return_value = None
        yield mock_A


@pytest.fixture
def runner(retrieve_token):
    """
    Fixture that returns the click cli runner.

    The runner is invoked when the function returned by this fixture is called.
    """
    runner_ = click.testing.CliRunner(mix_stderr=False)

    def _run(cmd, input=None):
        return runner_.invoke(
            dds_main,
            cmd,
            catch_exceptions=True,
            input=input,
        )

    yield _run
