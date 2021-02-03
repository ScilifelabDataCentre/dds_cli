"""CLI for the Data Delivery System."""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import logging
import pathlib
import sys

# Installed
import click

# Own modules
from cli_code import directory
from cli_code import logger
from cli_code import timestamp


###############################################################################
# MAIN ################################################################# MAIN #
###############################################################################


@click.group()
@click.option("--debug", default=False, is_flag=True)
@click.pass_context
def cli(ctx, debug):
    """Main CLI command, sets up DDS info."""

    # Timestamp
    t_s = timestamp.TimeStamp().timestamp

    # Path to new directory
    dds_dir = pathlib.Path.cwd() / pathlib.Path(f"DataDelivery_{t_s}")

    # Define alldirectories in DDS folder
    all_dirs = directory.DDSDirectory(path=dds_dir).directories

    # Path to log file
    logfile = str(all_dirs["LOGS"] / pathlib.Path("ds.log"))

    # Create logger
    log = logging.getLogger(__name__)
    log = logger.log_to_file(logger=log, filename=logfile)
    log = logger.log_to_terminal(logger=log)
    log.setLevel(logging.DEBUG if debug else logging.WARNING)

    # Create context object
    ctx.obj = {
        "TIMESTAMP": t_s,
        "DDS_DIRS": all_dirs,
        "LOGFILE": logfile,
        "LOGGER": log
    }


@cli.command()
@click.pass_obj
def test(dds_info):
    click.echo("testing")
    click.echo(dds_info)
