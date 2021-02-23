"""CLI for the Data Delivery System."""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import logging
import pathlib
import sys
import os
import concurrent.futures
import itertools

# Installed
import click
from rich import pretty
import rich.console

# Own modules
import cli_code
from cli_code import user
from cli_code import directory
from cli_code import timestamp
from cli_code import data_deliverer as dd

# Setup
pretty.install()
console = rich.console.Console()

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
@click.option("--break-on-fail", is_flag=True, default=False,
              show_default=True,
              help="Cancel upload of all files if one fails")
@click.option("--num-threads", "-nt", required=False, multiple=False,
              default=min(32, os.cpu_count() + 4), show_default=True,
              type=click.IntRange(1, 32),
              help="Number of parallel threads to perform the delivery.")
@click.pass_obj
def put(dds_info, config, username, project, recipient, source,
        source_path_file, break_on_fail, num_threads):
    """Processes and uploads specified files to the cloud."""

    # Get logger
    log = dds_info["LOGGER"]

    # Begin delivery
    with dd.DataDeliverer(config=config, username=username, project=project,
                          recipient=recipient, source=source,
                          source_path_file=source_path_file,
                          break_on_fail=break_on_fail) as delivery:
        console.print(delivery.data.data)

        # Keep track of futures
        upload_threads = {}     # Upload related
        db_threads = {}         # Database related

        # Iterator to keep track of which files have been handled
        iterator = iter(delivery.data.data.copy())

        with concurrent.futures.ThreadPoolExecutor() as texec:

            # Schedule the first num_threads futures for upload
            for file in itertools.islice(iterator, num_threads):
                log.debug("Uploading file %s...", file)
                upload_threads[
                    texec.submit(delivery.put, file=file)
                ] = file

            # Continue until all files are done
            while upload_threads:
                # Wait for the next future to complete
                udone, _ = concurrent.futures.wait(
                    upload_threads,
                    return_when=concurrent.futures.FIRST_COMPLETED
                )

                # Get result from future and schedule database update
                for ufut in udone:
                    uploaded_file = upload_threads.pop(ufut)
                    log.debug("...File %s uploaded!", uploaded_file)

                    # Get result
                    try:
                        _ = ufut.result()
                    except concurrent.futures.BrokenExecutor as err:
                        log.critical("Upload of file %s failed! Error: %s",
                                     uploaded_file, err)
                        continue

                    # Schedule file for db update
                    log.debug("Adding to db: %s...", uploaded_file)
                    db_threads[
                        texec.submit(delivery.add_file_db, file=uploaded_file)
                    ] = uploaded_file

                new_tasks = 0

                # Continue until all files are done
                while db_threads:
                    # Wait for the next future to complete
                    done_db, _ = concurrent.futures.wait(
                        db_threads,
                        return_when=concurrent.futures.FIRST_COMPLETED
                    )

                    # Get result from future
                    for fut_db in done_db:
                        added_file = db_threads.pop(fut_db)
                        log.debug("...File added to db: %s", added_file)

                        new_tasks += 1

                        # Get result
                        try:
                            _ = fut_db.result()
                        except concurrent.futures.BrokenExecutor as err:
                            log.critical(
                                "Adding of file %s to database failed! "
                                "Error: %s", uploaded_file, err
                            )
                            continue

                # Schedule the next set of futures for upload
                for ufile in itertools.islice(iterator, len(done_db)):
                    log.debug("Uploading file %s...", ufile)
                    upload_threads[
                        texec.submit(delivery.put, file=ufile)
                    ] = ufile



# @cli.command()
# @click.argument("proj_arg", required=False)
# @click.option("--project", "-p", required=False)
# @click.option("--config", "-c", required=False, type=click.Path(exists=True),
#               help="Path to file with user credentials, destination, etc.")
# @click.option("--username", "-u", required=False, type=str,
#               help="Your Data Delivery System username.")
# @click.pass_obj
# def ls(dds_info, proj_arg, project, config, username):
#     """List the projects and the files within the projects."""

#     project = proj_arg if proj_arg is not None else project
#     with dd.DataLister(project=project, config=config, username=username) as dl:
#         pass