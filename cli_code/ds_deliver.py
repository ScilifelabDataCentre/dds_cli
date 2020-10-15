"""
Command line interface for the Data Delivery System

TODO(ina): This should be some information about the cli and how to use it.

    And here there should be an example or two:

    example 1:

    example 2:
"""

# TODO(ina): Fix or ignore pylint "too-many-arguments" warnings etc

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import concurrent.futures
import logging
import logging.config
import sys

# Installed
import click
import requests

# Own modules
from cli_code import data_deliverer as dd
from cli_code import ENDPOINTS
from cli_code import exceptions_ds
from cli_code import file_handler
from cli_code import s3_connector


###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Setup logging
CLI_LOGGER = logging.getLogger(__name__)
CLI_LOGGER.setLevel(logging.WARNING)


###############################################################################
# MAIN ################################################################# MAIN #
###############################################################################


@click.group()
def cli():
    """TODO(ina): Write a docstring here."""

    CLI_LOGGER.info("Beginning data delivery...")


###############################################################################
# PUT ################################################################### PUT #
###############################################################################


@cli.command()
@click.option('--creds', '-c',
              required=False,
              type=click.Path(exists=True),
              help="Path to config file containing e.g. username, password, "
                   "project id, etc.")
@click.option('--username', '-u',
              required=False,
              type=str,
              help="Delivery Portal username.")
@click.option('--password', '-pw',
              required=False,
              type=str,
              help="Delivery Portal password.")
@click.option('--project', '-p',
              required=False,
              type=str,
              help="Project to upload files to.")
@click.option('--owner', '-o',
              required=True,
              type=str,
              multiple=False,
              default="",
              show_default=True,
              help="The owner of the data.")
@click.option('--pathfile', '-f',
              required=False,
              type=click.Path(exists=True),
              multiple=False,
              help="Path to file containing all files and "
                   "folders to be uploaded.")
@click.option('--data', '-d',
              required=False,
              type=click.Path(exists=True),
              multiple=True,
              help="Path to file or folder to upload.")
@click.option('--break-on-fail/--nobreak-on-fail', default=True, show_default=True)
@click.option('--overwrite', is_flag=True, default=False, show_default=True)
def put(creds: str, username: str, password: str, project: str,
        owner: str, pathfile: str, data: tuple, break_on_fail=True,
        overwrite=False) -> (str):
    """Uploads the files to S3 bucket. Only usable by facilities."""

    # TODO(ina): Check if usage information is needed here
    # or if click handles it.

    # Create DataDeliverer to handle files and folders
    with dd.DataDeliverer(creds=creds, username=username, password=password,
                          project_id=project, project_owner=owner,
                          pathfile=pathfile, data=data,
                          break_on_fail=break_on_fail, overwrite=overwrite) \
            as delivery:

        # POOLEXECUTORS STARTED ####################### POOLEXECUTORS STARTED #
        pool_executor = concurrent.futures.ProcessPoolExecutor()   # Processing
        thread_executor = concurrent.futures.ThreadPoolExecutor()  # IO related

        # Futures -- Pools and threads
        pools = {}          # Processing e.g. compression, encryption etc
        threads = {}        # Upload to S3
        final_threads = {}  # Delete files

        # BEGIN DELIVERY # # # # # # # # # # # # # # # # # # # BEGIN DELIVERY #
        # Process files - Compression, encryption, etc
        for path, info in delivery.data.items():

            # Quit and move on if DS noted cancelation for file
            if not info['proceed']:
                CLI_LOGGER.warning("CANCELLED: '%s'", path)
                delivery.update_progress_bar(
                    file=path, status='e')  # -> X-symbol
                continue

            # Display progress = "Encrypting..."
            delivery.update_progress_bar(file=path, status='enc')

            # Start file processing
            pools[
                pool_executor.submit(delivery.prep_upload,
                                     path=path,
                                     path_info=delivery.data[path])
            ] = path

        # Get results from processing and upload to S3
        for pfuture in concurrent.futures.as_completed(pools):
            ppath = pools[pfuture]      # Original file path -- keep track
            try:
                processed, efile, esize, \
                    ds_compressed, key, salt, error = pfuture.result()
            except concurrent.futures.BrokenExecutor:
                sys.exit(f"{pfuture.exception()}")
                break  # Precaution if sys.exit not quit completely

            # Update file info
            proceed = delivery.update_delivery(
                file=ppath,
                updinfo={'proceed': processed,
                         'encrypted_file': efile,
                         'encrypted_size': esize,
                         'ds_compressed': ds_compressed,
                         'error': error,
                         'key': key,
                         'salt': salt}
            )
            CLI_LOGGER.debug("PUBLIC KEY for file '%s': '%s'", ppath, key)

            # Set processing as finished
            delivery.set_progress(item=ppath, processing=True, finished=True)

            # Quit and move on if DS noted cancelation for file
            if not proceed:
                CLI_LOGGER.warning("CANCELLED: '%s'", ppath)
                delivery.update_progress_bar(
                    file=ppath, status='e')  # -> X-symbol
                continue

            # Display progress = "Uploading..."
            delivery.update_progress_bar(file=ppath, status='u')

            # Start upload
            threads[
                thread_executor.submit(delivery.put,
                                       file=ppath,
                                       fileinfo=delivery.data[ppath])
            ] = ppath

        # FINISH DELIVERY # # # # # # # # # # # # # # # # # # FINISH DELIVERY #
        # Update database
        for ufuture in concurrent.futures.as_completed(threads):
            upath = threads[ufuture]       # Original file path -- keep track
            try:
                uploaded, error = ufuture.result()
            except concurrent.futures.BrokenExecutor:
                sys.exit(f"{ufuture.exception()}")
                break  # Precaution if sys.exit not quit completely

            # Update file info
            proceed = delivery.update_delivery(file=upath,
                                               updinfo={'proceed': uploaded,
                                                        'error': error})

            # Set upload as finished
            delivery.set_progress(item=upath, upload=True, finished=True)

            # Quit and move on if DS noted cancelation for file
            if not proceed:
                CLI_LOGGER.warning("CANCELLED: '%s'", upath)
                delivery.update_progress_bar(
                    file=upath, status='e')  # -> X-symbol
                continue

            CLI_LOGGER.info("UPLOAD COMPLETED: '%s' -> '%s'",
                            upath, delivery.data[upath]['new_file'])

            # Set db update as in progress
            delivery.set_progress(item=upath, db=True, started=True)

            # TODO(ina): Put db update request in function - threaded?
            req_args = {
                'project': delivery.project_id,
                'file': delivery.data[upath]['new_file'],
                'directory_path': delivery.data[upath]['directory_path'],
                'size': delivery.data[upath]['size'],
                'ds_compressed': delivery.data[upath]['ds_compressed'],
                'key': delivery.data[upath]['key'],
                'salt': delivery.data[upath]['salt'],
                'overwrite': delivery.overwrite
            }

            req = ENDPOINTS['update_file']
            response = requests.post(req, params=req_args)

            if not response.ok:
                sys.exit(exceptions_ds.printout_error(
                    f"Could not update database. {response.text}"
                ))

            db_response = response.json()
            if not db_response['updated']:
                emessage = f"Database update failed: {db_response['message']}"
                CLI_LOGGER.warning(emessage)
                with s3_connector.S3Connector(bucketname=delivery.bucketname,
                                              project=delivery.s3project) \
                        as s3_conn:
                    s3_conn.delete_item(key=key)
                delivery.update_progress_bar(file=upath, status='e')
                continue

            CLI_LOGGER.info("DATABASE UPDATE SUCCESSFUL: '%s'", upath)

            # Set delivery as finished and display progress = check mark
            delivery.set_progress(item=upath, db=True, finished=True)
            delivery.update_progress_bar(file=upath, status='f')
            encrypted_file = delivery.data[upath]['encrypted_file']

            # Delete encrypted files as soon as success
            final_threads[
                thread_executor.submit(file_handler.file_deleter,
                                       file=encrypted_file)
            ] = (upath, encrypted_file)

        # Check if deletion successful
        for dfuture in concurrent.futures.as_completed(final_threads):
            origpath, cryptpath = final_threads[dfuture]
            try:
                deleted, _ = dfuture.result()
            except concurrent.futures.BrokenExecutor:
                CLI_LOGGER.critical("%s", dfuture.exception())
                continue

            if deleted:
                CLI_LOGGER.info("File deleted: '%s' ('%s')",
                                cryptpath, origpath)
            else:
                CLI_LOGGER.warning("Failed to delete file: '%s' ('%s')",
                                   cryptpath, origpath)

        # DELIVERY FINISHED ------------------------------- DELIVERY FINISHED #

        # STOPPING POOLEXECUTORS ##################### STOPPING POOLEXECUTORS #
        pool_executor.shutdown(wait=True)
        thread_executor.shutdown(wait=True)
        sys.stdout.write("\n")


###############################################################################
# GET ################################################################### GET #
###############################################################################


@cli.command()
@click.option('--creds', '-c',
              required=False,
              type=click.Path(exists=True),
              help="Path to creds file containing e.g. username, password, "
                   "project id, etc.")
@click.option('--username', '-u',
              required=False,
              type=str,
              help="Delivery Portal username.")
@click.option('--password', '-pw',
              required=False,
              type=str,
              help="Delivery Portal password.")
@click.option('--project', '-p',
              required=False,
              type=str,
              help="Project to upload files to.")
@click.option('--pathfile', '-f',
              required=False,
              multiple=False,
              type=click.Path(exists=True),
              help="Path to file containing all files and "
                   "folders to be uploaded.")
@click.option('--data', '-d',
              required=False,
              multiple=True,
              type=str,
              help="Path to file or folder to upload.")
@click.option('--break-on-fail/--nobreak-on-fail', default=True, show_default=True)
def get(creds: str, username: str, password: str, project: str,
        pathfile: str, data: tuple, break_on_fail: bool = True):
    """Downloads the files from S3 bucket. Not usable by facilities. """

    with dd.DataDeliverer(creds=creds, username=username, password=password,
                          project_id=project, pathfile=pathfile, data=data,
                          break_on_fail=break_on_fail) \
            as delivery:

        # POOLEXECUTORS STARTED ####################### POOLEXECUTORS STARTED #
        pool_executor = concurrent.futures.ProcessPoolExecutor()   # Processing
        thread_executor = concurrent.futures.ThreadPoolExecutor()  # IO related

        # Futures -- Pools and threads
        pools = {}          # Finalizing e.g. decompression, decryption etc
        threads = {}        # Download from S3

        # BEGIN DELIVERY # # # # # # # # # # # # # # # # # # # BEGIN DELIVERY #
        # Download from S3
        for path, info in delivery.data.items():

            # If DS noted cancelation for file -- quit and move on
            if not info['proceed']:
                CLI_LOGGER.warning("Cancelled: '%s'", path)
                delivery.update_progress_bar(file=path, status='e')  # -> X
                continue

            # Display progress = "Downloading..."
            delivery.update_progress_bar(file=path, status='d')

            # Start download from S3
            threads[
                thread_executor.submit(delivery.get, path=path, path_info=info)
            ] = path

        # Get result and finalize - decrypt, decompress etc.
        for dfuture in concurrent.futures.as_completed(threads):
            dpath = threads[dfuture]  # Original file path -- keep track
            try:
                downloaded, error = dfuture.result()
            except concurrent.futures.BrokenExecutor:
                sys.exit(f"{dfuture.exception()}")
                break   # Precaution if sys.exit not quit completely

            # Update file info
            proceed = delivery.update_delivery(file=dpath,
                                               updinfo={'proceed': downloaded,
                                                        'error': error})

            # Set file upload as finished
            delivery.set_progress(item=dpath, download=True, finished=True)

            # Quit and move on if DS noted cancelation for file
            if not proceed:
                CLI_LOGGER.warning("Cancelled: '%s'", dpath)
                delivery.update_progress_bar(file=dpath, status='e')  # -> X
                continue

            CLI_LOGGER.info("DOWNLOAD COMPLETED: '%s' -> '%s'",
                            dpath, delivery.data[dpath]['new_file'])

            # Display progress = "Decrypting..."
            delivery.update_progress_bar(file=dpath, status='dec')

            # Start file finalizing -- decompression, decryption, etc.
            pools[
                pool_executor.submit(delivery.finalize_delivery,
                                     file=dpath,
                                     fileinfo=delivery.data[dpath])
            ] = dpath

        # FINISH DELIVERY # # # # # # # # # # # # # # # # # # FINISH DELIVERY #
        # Update database
        for ffuture in concurrent.futures.as_completed(pools):
            fpath = pools[ffuture]  # Original file path -- keep track
            try:
                decrypted, decrypted_file, error = ffuture.result()
            except concurrent.futures.BrokenExecutor:
                sys.exit(f"{ffuture.exception()}")
                break  # Precaution if sys.exit not quit completely

            # Update file info
            proceed = delivery.update_delivery(
                file=fpath,
                updinfo={'proceed': decrypted,
                         'decrypted_file': decrypted_file,
                         'error': error}
            )

            # Set file finalizing as finished
            delivery.set_progress(item=fpath,
                                  decryption=True,
                                  finished=True)

            # If DS noted cancelation for file -- quit and move on
            if not proceed:
                CLI_LOGGER.warning("File: '%s' -- cancelled "
                                   "-- moving on to next file", fpath)
                delivery.update_progress_bar(file=fpath, status='e')  # -> X
                continue

            # Set file db update to in progress
            delivery.set_progress(item=fpath, db=True, started=True)

            req = ENDPOINTS['delivery_date']
            args = {'file_id': delivery.data[fpath]['id']}
            response = requests.post(req, params=args)

            if not response.ok:
                emessage = f"File: {fpath}. Database update failed."
                delivery.update_progress_bar(
                    file=fpath, status='e')  # -> X-symbol
                CLI_LOGGER.warning(emessage)
            else:
                CLI_LOGGER.info("DATABASE UPDATE SUCCESSFUL: '%s'", fpath)

                # Set delivery as finished and display progress = check mark
                delivery.set_progress(item=fpath, db=True, finished=True)
                delivery.update_progress_bar(file=fpath, status='f')

        # DELIVERY FINISHED ------------------------------- DELIVERY FINISHED #

        # STOPPING POOLEXECUTORS ##################### STOPPING POOLEXECUTORS #
        pool_executor.shutdown(wait=True)
        thread_executor.shutdown(wait=True)
        sys.stdout.write("\n")
