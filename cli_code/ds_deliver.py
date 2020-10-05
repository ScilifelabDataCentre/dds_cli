"""
Command line interface for Data Delivery System

TODO: Info here?
"""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import logging
import logging.config
import sys
from concurrent.futures import (ProcessPoolExecutor, ThreadPoolExecutor,
                                as_completed)

# Installed
import click
import requests

# Own modules
import cli_code.file_handler as fh
from cli_code import API_BASE, ENDPOINTS
from cli_code.data_deliverer import DataDeliverer
from cli_code.exceptions_ds import (PoolExecutorError, printout_error)
from cli_code.s3_connector import S3Connector


###############################################################################
# MAIN ################################################################# MAIN #
###############################################################################


@click.group()
def cli():

    # Setup logging
    global CLI_LOGGER
    CLI_LOGGER = logging.getLogger(__name__)
    CLI_LOGGER.setLevel(logging.WARNING)


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
@click.option('--break-on-fail', is_flag=True, default=True, show_default=True)
@click.option('--overwrite', is_flag=True, default=False, show_default=True)
@click.option('--encrypt/--dont-encrypt', default=True, show_default=True)
def put(creds: str, username: str, password: str, project: str,
        owner: str, pathfile: str, data: tuple, break_on_fail=True,
        overwrite=False, encrypt=True) -> (str):
    """Uploads the files to S3 bucket. Only usable by facilities. """

    # Create DataDeliverer to handle files and folders
    with DataDeliverer(creds=creds, username=username, password=password,
                       project_id=project, project_owner=owner,
                       pathfile=pathfile, data=data,
                       break_on_fail=break_on_fail, overwrite=overwrite,
                       encrypt=encrypt) \
            as delivery:

        # POOLEXECUTORS STARTED ####################### POOLEXECUTORS STARTED #
        pool_executor = ProcessPoolExecutor()       # Processing
        thread_executor = ThreadPoolExecutor()      # IO related tasks

        # Futures -- Pools and threads
        pools = {}          # Processing e.g. compression, encryption etc
        threads = {}        # Upload to S3
        final_threads = {}  # Delete files

        # BEGIN DELIVERY # # # # # # # # # # # # # # # # # # # BEGIN DELIVERY #
        # Process files - Compression, encryption, etc
        for path, info in delivery.data.items():

            # Quit and move on if DS noted cancelation for file
            if not info['proceed']:
                CLI_LOGGER.warning(f"CANCELLED: '{path}'")
                delivery.update_progress_bar(file=path, status='e')  # -> X-symbol
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
        for pfuture in as_completed(pools):
            ppath = pools[pfuture]      # Original file path -- keep track
            try:
                processed, efile, esize, \
                    ds_compressed, key, salt, error = pfuture.result()
            except PoolExecutorError:
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
            CLI_LOGGER.debug(f"PUBLIC KEY for file {ppath}: {key}")

            # Set processing as finished
            delivery.set_progress(item=ppath, processing=True, finished=True)

            # Quit and move on if DS noted cancelation for file
            if not proceed:
                CLI_LOGGER.warning(f"CANCELLED: '{ppath}'")
                delivery.update_progress_bar(file=ppath, status='e')  # -> X-symbol
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
        for ufuture in as_completed(threads):
            upath = threads[ufuture]       # Original file path -- keep track
            try:
                uploaded, error = ufuture.result()
            except PoolExecutorError:
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
                CLI_LOGGER.warning(f"CANCELLED: '{upath}'")
                delivery.update_progress_bar(file=upath, status='e')  # -> X-symbol
                continue

            CLI_LOGGER.info(f"UPLOAD COMPLETED: {upath} "
                            f" -> {delivery.data[upath]['new_file']}")

            # Set db update as in progress
            delivery.set_progress(item=upath, db=True, started=True)

            # TODO: COUCHDB -> MARIADB
            # TODO: DATABASE UPDATE TO BE THREADED - PROBLEMS WITH COUCHDB ATM
            req_args = {
                'project': delivery.project_id,
                'file': delivery.data[upath]['new_file'],
                'directory_path': delivery.data[upath]['directory_path'],
                'size': delivery.data[upath]['size'],
                'ds_compressed': delivery.data[upath]['ds_compressed'],
                'key': delivery.data[upath]['key'],
                'salt': delivery.data[upath]['salt']
            }

            req = ENDPOINTS['update_file']
            response = requests.post(req, params=req_args)

            if not response.ok:
                sys.exit(printout_error(
                    "Could not update database."
                ))

            db_response = response.json()
            if not db_response['updated']:
                emessage = f"Database update failed: {db_response['message']}"
                CLI_LOGGER.warning(emessage)
                with S3Connector(bucketname=delivery.bucketname,
                                 project=delivery.s3project) as s3:
                    s3.delete_item(key=key)
                delivery.update_progress_bar(file=upath, status='e')
                continue

            CLI_LOGGER.info("DATABASE UPDATE SUCCESSFUL: {upath}")

            # Set delivery as finished and display progress = check mark
            delivery.set_progress(item=upath, db=True, finished=True)
            delivery.update_progress_bar(file=upath, status='f')
            encrypted_file = delivery.data[upath]['encrypted_file']

            # Delete encrypted files as soon as success
            final_threads[
                thread_executor.submit(fh.file_deleter,
                                       file=encrypted_file)
            ] = (upath, encrypted_file)

        # Check if deletion successful
        for dfuture in as_completed(final_threads):
            origpath, cryptpath = final_threads[dfuture]
            try:
                deleted, derror = dfuture.result()
            except PoolExecutorError:
                CLI_LOGGER.critical(f"{ufuture.exception()}")
                continue

            if deleted:
                CLI_LOGGER.info(f"File deleted: {cryptpath} ({origpath})")
            else:
                CLI_LOGGER.warning(
                    f"Failed to delete file: {cryptpath} ({origpath})"
                )

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
def get(creds: str, username: str, password: str, project: str,
        pathfile: str, data: tuple):
    """Downloads the files from S3 bucket. Not usable by facilities. """

    with DataDeliverer(creds=creds, username=username, password=password,
                       project_id=project, pathfile=pathfile, data=data) \
            as delivery:

        # POOLEXECUTORS STARTED ####################### POOLEXECUTORS STARTED #
        pool_executor = ProcessPoolExecutor()       # Processing
        thread_executor = ThreadPoolExecutor()      # IO related tasks

        # Futures -- Pools and threads
        pools = {}          # Finalizing e.g. decompression, decryption etc
        threads = {}        # Download from S3

        # BEGIN DELIVERY # # # # # # # # # # # # # # # # # # # BEGIN DELIVERY #
        # Download from S3
        for path, info in delivery.data.items():

            # If DS noted cancelation for file -- quit and move on
            if not info['proceed']:
                CLI_LOGGER.warning(f"Cancelled: '{path}'")
                delivery.update_progress_bar(file=path, status='e')  # -> X-symbol
                continue

            # Display progress = "Downloading..."
            delivery.update_progress_bar(file=path, status='d')

            # Start download from S3
            threads[
                thread_executor.submit(delivery.get, path=path, path_info=info)
            ] = path

        # Get result and finalize - decrypt, decompress etc.
        for dfuture in as_completed(threads):
            dpath = threads[dfuture]  # Original file path -- keep track
            try:
                downloaded, error = dfuture.result()
            except PoolExecutorError:
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
                CLI_LOGGER.warning(f"Cancelled: '{dpath}'")
                delivery.update_progress_bar(file=dpath, status='e')  # -> X-symbol
                continue

            CLI_LOGGER.info(f"DOWNLOAD COMPLETED: {dpath} "
                            f" -> {delivery.data[dpath]['new_file']}")

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
        for ffuture in as_completed(pools):
            fpath = pools[ffuture]  # Original file path -- keep track
            try:
                decrypted, decrypted_file, error = ffuture.result()
            except PoolExecutorError:
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
                CLI_LOGGER.warning(f"File: '{fpath}' -- cancelled "
                                   "-- moving on to next file")
                delivery.update_progress_bar(file=fpath, status='e')  # -> X-symbol
                continue

            # Set file db update to in progress
            delivery.set_progress(item=fpath, db=True, started=True)

            req = ENDPOINTS['delivery_date']
            args = {'file_id': delivery.data[fpath]['id']}
            response = requests.post(req, params=args)

            if not response.ok:
                emessage = f"File: {fpath}. Database update failed."
                delivery.update_progress_bar(file=fpath, status='e')  # -> X-symbol
                CLI_LOGGER.warning(emessage)
            else:
                CLI_LOGGER.info(f"DATABASE UPDATE SUCCESSFUL: {fpath}")

                # Set delivery as finished and display progress = check mark
                delivery.set_progress(item=fpath, db=True, finished=True)
                delivery.update_progress_bar(file=fpath, status='f')

        # DELIVERY FINISHED ------------------------------- DELIVERY FINISHED #

        # STOPPING POOLEXECUTORS ##################### STOPPING POOLEXECUTORS #
        pool_executor.shutdown(wait=True)
        thread_executor.shutdown(wait=True)
        sys.stdout.write("\n")
