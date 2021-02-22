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

        # Keep track of futures
        upload_threads = {}     # Upload related
        db_threads = {}         # Database related
        
        iterator = iter(delivery.data.data.copy())

        with concurrent.futures.ThreadPoolExecutor() as executor:

            # Schedule the first N futures.  We don't want to schedule them all
            # at once, to avoid consuming excessive amounts of memory.
            for file in itertools.islice(iterator, num_threads):
                log.debug("Uploading file %s...", file)
                upload_threads[
                    executor.submit(delivery.put, file=file)
                ] = file

            while upload_threads:

                # Wait for the next future to complete.
                done, _ = concurrent.futures.wait(
                    upload_threads, return_when=concurrent.futures.FIRST_COMPLETED
                )
                
                for fut in done:
                    uploaded_file = upload_threads.pop(fut)
                    log.debug("...File %s uploaded!", uploaded_file)

                    log.debug("Adding to db: %s...", uploaded_file)
                    db_threads[
                        executor.submit(delivery.add_file_db, file=uploaded_file)
                    ] = uploaded_file

                while db_threads:
                    done_db, _ = concurrent.futures.wait(
                        db_threads, return_when=concurrent.futures.FIRST_COMPLETED
                    )
                    log.debug("\nThreads:\tUpload %s\tDB %s\n", len(upload_threads), len(db_threads))

                    for fut_db in done_db:
                        added_file = db_threads.pop(fut_db)
                        log.debug("...File added to db: %s", added_file)

                for ufile in itertools.islice(iterator, len(done)):
                    log.debug("Uploading file %s...", ufile)
                    upload_threads[
                        executor.submit(delivery.put, file=ufile)
                    ] = ufile
                


                
                # new_tasks = 0

                # for fut in done:
                #     original_task = upload_threads.pop(fut)
                #     print(f"The outcome of {original_task} is {fut.result()}")
                #     try:
                #         _ = all_files.pop(original_task)
                #     except Exception as err:
                #         log.warning(err)
                #     else:
                #         log.info("Deleted %s from dict. Dict now looks like: \n %s", original_task, all_files)
                    
                #     if fut.result():
                #         print(f"The file {original_task} has been uploaded!")
                    
                #     new_tasks += 1

                # # Schedule the next set of futures.  We don't want more than N futures
                # # in the pool at a time, to keep memory consumption down.
                # for task in itertools.islice(list(all_files), new_tasks):
                #     upload_threads[
                #         executor.submit(delivery.put, file=task)
                #     ] = task

            

        # CORRECT BELOW -------------------------------------------------------
        # with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as t_exec:

        #     # Upload --------------------------------------------- Upload #
        #     for file, _ in list(delivery.data.data.items()):
        #         # Upload file to S3 in thread
        #         upload_threads[
        #             t_exec.submit(delivery.put, file=file)
        #         ] = file

        #     # When each file is uploaded ------ When each file is uploaded #
        #     for upload_future in concurrent.futures.as_completed(upload_threads):
        #         uploaded_file = upload_threads[upload_future]

        #         log.debug(uploaded_file)
        #         # Get returned info
        #         try:
        #             uploaded = upload_future.result()
        #             if not uploaded:
        #                 log.warning("File '%s' not uploaded!", uploaded_file)
        #                 break
        #         except concurrent.futures.BrokenExecutor:
        #             sys.exit(f"{upload_future.exception()}")
        #             break

        #         # Add to db ------------------------------------ Add to db #
        #         db_threads[
        #             t_exec.submit(delivery.add_file_db, file=uploaded_file)
        #         ] = uploaded_file

        #     # When db update done -------------------- When db update done #
        #     for db_future in concurrent.futures.as_completed(db_threads):
        #         added_file = db_threads[db_future]
        #         print(added_file)
        #         # Get returned info
        #         try:
        #             log.debug("Getting result for file '%s'...", added_file)
        #             file_added = db_future.result()
        #             log.debug("...Result for file '%s'", added_file)
        #             # Error if >db update< failed
        #             if not file_added:
        #                 # TODO (ina): Change here - don't quit
        #                 log.warning("File '%s' not added to database!", added_file)
        #                 break
        #         except concurrent.futures.BrokenExecutor:
        #             log.exception("Error! %s", db_future.exception())

        #         log.debug("Finished -- '%s' : '%s'", added_file, file_added)
