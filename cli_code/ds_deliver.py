"""CLI for the Data Delivery System."""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import logging
import pathlib
import sys
import os
import concurrent.futures as futures

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
@click.option("--num_threads", "-nt", default=min(32, os.cpu_count() + 4),
              type=click.IntRange(1,32), required=False, multiple=False,
              help="Number of parallel threads to perform the delivery.")
@click.pass_obj
def put(dds_info, config, username, project, recipient, source,
        source_path_file, num_threads):
    """Processes and uploads specified files to the cloud."""

    # Get logger
    log = dds_info["LOGGER"]

    # Begin delivery
    with dd.DataDeliverer(config=config, username=username, project=project,
                          recipient=recipient, source=source,
                          source_path_file=source_path_file) as delivery:

        upload_threads = {}
        db_threads = {}

        with futures.ThreadPoolExecutor(max_workers=num_threads) as t_exec:

            for file in delivery.data.data:
                # Upload file to S3 in thread
                upload_threads[
                    t_exec.submit(delivery.put, file=file)
                ] = file

            # Continue when each file is uploaded
            for upload_future in futures.as_completed(upload_threads):
                uploaded_file = upload_threads[upload_future]

                # Get returned info
                try:
                    uploaded = upload_future.result()
                except futures.BrokenExecutor():
                    sys.exit(f"{upload_future.exception()}")
                    break

                if not uploaded:
                    # TODO (ina): Change here - don't quit
                    sys.exit("Failed: Upload of file '%s' failed!",
                             uploaded_file)

                # Add file to db in thread
                db_threads[
                    t_exec.submit(delivery.add_file_db, file=uploaded_file)
                ] = uploaded_file

            for db_future in futures.as_completed(db_threads):
                added_file = db_threads[db_future]

                # Get returned info
                try:
                    file_added = db_future.result()
                except futures.BrokenExecutor():
                    log.exception("Error! %s", db_future.exception())

                log.debug("Added file: %s", added_file)
                log.debug("File added to db: %s", file_added)
                if not file_added:
                    # TODO (ina): Change here - don't quit
                    log.exception("Failed: File '%s' not added to database!", added_file)

                log.debug("Finished -- '%s' : '%s'", added_file, file_added)
