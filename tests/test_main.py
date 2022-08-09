from datetime import datetime
from dds_cli import __main__
from unittest.mock import patch
import datetime
import pytest
import click.testing
import dds_cli
from _pytest.capture import CaptureFixture


@pytest.fixture
def runner() -> click.testing.CliRunner:
    return click.testing.CliRunner()


def mock_list_all_active_motds():
    return [
        {
            "MOTD ID": 1,
            "Message": "This is a MOTD",
            "Created": "2022-08-09 17:08",
        },
    ]


def test_active_motds_before_call(runner: click.testing.CliRunner) -> None:
    with patch(
        "dds_cli.motd_manager.MotdManager.list_all_active_motds", mock_list_all_active_motds
    ):
        _: click.testing.Result = runner.invoke(__main__.dds_main)
