"""CLI for the Data Delivery System."""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import logging
import pathlib
import sys
import concurrent

# Installed
import click

# Own modules
import cli_code
from cli_code import user
from cli_code import directory
from cli_code import timestamp
from cli_code import data_deliverer as dd


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
    cli_code.setup_custom_logger(filename=logfile, debug=debug)

    LOG = logging.getLogger(__name__)
    LOG.setLevel(logging.DEBUG if debug else logging.WARNING)

    # Create context object
    ctx.obj = {
        "TIMESTAMP": t_s,
        "DDS_DIRS": all_dirs,
        "LOGFILE": logfile,
        "LOGGER": LOG
    }


@cli.command()
@click.option("--config", "-c", required=False, type=click.Path(exists=True),
              help="Path to file with user credentials, destination, etc.")
@click.option("--username", "-u", required=False, type=str,
              help="Your Data Delivery System username.")
@click.option("--project", "-p", required=False, type=str,
              help="Project ID to which you're uploading data.")
@click.option("--recipient", "-r", required=False, type=str,
              help="ID of the user which owns the data.")
@click.option("--source", "-s", required=False, type=click.Path(exists=True),
              multiple=True, help="Path to file or directory (local).")
@click.option("--source-path-file", "-spf", required=False,
              type=click.Path(exists=True), multiple=False,
              help="File containing path to files or directories. ")
@click.pass_obj
def put(dds_info, config, username, project, recipient, source,
        source_path_file):
    """Processes and uploads specified files to the cloud."""

    # Get logger
    log = dds_info["LOGGER"]
    with dd.DataDeliverer(config=config, username=username, project=project,
                          recipient=recipient, source=source,
                          source_path_file=source_path_file) as delivery:

        for file in delivery.data.data:
            delivery.put(file)
