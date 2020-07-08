"""
Command line interface for Data Delivery System
"""

# IMPORTS ########################################################### IMPORTS #

from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, \
    as_completed
import logging
import logging.config
from pathlib import Path
import sys
import os
import itertools

import click
from cli_code.crypt4gh.crypt4gh import lib, header, keys

from cli_code import LOG_FILE, timestamp
from cli_code.data_deliverer import DataDeliverer, finish_download
from cli_code.crypto_ds import Crypt4GHKey
from cli_code.database_connector import DatabaseConnector
from cli_code.exceptions_ds import DataException
import cli_code.file_handler as fh
from cli_code.s3_connector import S3Connector

###############################################################################
# Logging ########################################################### Logging #
###############################################################################

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)


def config_logger(logfile: str):
    '''Creates log file '''

    return fh.config_logger(logger=LOG, filename=logfile,
                            file=True, file_setlevel=logging.DEBUG,
                            fh_format="%(asctime)s::%(levelname)s::" +
                            "%(name)s::%(lineno)d::%(message)s",
                            stream=True, stream_setlevel=logging.DEBUG,
                            sh_format="%(levelname)s::%(name)s::" +
                            "%(lineno)d::%(message)s")

###############################################################################
# MAIN ################################################################# MAIN #
###############################################################################


@click.group()
def cli():
    global COMPRESSED_FORMATS

###############################################################################
# PUT ################################################################### PUT #
###############################################################################


@cli.command()
@click.option('--config', '-c',
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
@click.option('--break-on-fail', is_flag=True)
def put(config: str, username: str, password: str, project: str,
        owner: str, pathfile: str, data: tuple, break_on_fail) -> (str):
    """Uploads the files to S3 bucket. Only usable by facilities. """

    # Create DataDeliverer to handle files and folders
    with DataDeliverer(config=config, username=username, password=password,
                       project_id=project, project_owner=owner,
                       pathfile=pathfile, data=data, break_on_fail=True) \
            as delivery:

        # Setup logging
        CLI_LOGGER = config_logger(LOG_FILE)

        # POOLEXECUTORS STARTED ####################### POOLEXECUTORS STARTED #
        pool_executor = ProcessPoolExecutor()       # Processing
        thread_executor = ThreadPoolExecutor()      # IO related tasks

        # Futures -- Pools and threads
        pools = {}      # Processing e.g. compression, encryption etc
        cthreads = {}   # Initial checking e.g. file formats etc
        uthreads = {}   # Upload to S3

        # BEGIN DELIVERY -- ITERATE THROUGH ALL FILES
        for path, info in delivery.data.items():
            # CLI_LOGGER.debug(f"Beginning...{path}: {info}\n")  # Print out before

            # If DS noted cancelation for file -- quit and move on
            if not info['proceed']:
                CLI_LOGGER.warning(f"File: '{path}' -- cancelled "
                                   "-- moving on to next file")
                continue

            # Start initial file checks and save future to dict
            cthreads[
                thread_executor.submit(delivery.do_file_checks,
                                       file=path,
                                       fileinfo=info)
            ] = path

        # PROCESS FILES -- COMPRESSION, ENCRYPTION, ETC.
        # When initial check for a file is done -- move on to processing
        for cfuture in as_completed(cthreads):
            cpath = cthreads[cfuture]       # Original file path -- keep track
            proceed, compressed, new_file, error = cfuture.result()  # Get info
            # CLI_LOGGER.debug(f"file: {cpath}\t proceed: {proceed}\t"
            #                  f"compressed: {compressed}\t new_file: "
            #                  f"{new_file}\t error: {error}")

            # Update file info
            delivery.update_delivery(file=cpath,
                                     updinfo={"proceed": proceed,
                                              "compressed": compressed,
                                              "new_file": new_file,
                                              "error": error})
            # Set file check as finished
            delivery.set_progress(item=cpath, check=True, finished=True)
            # CLI_LOGGER.debug(f"File: {cpath}, Info: {delivery.data[cpath]}")

            # If DS noted cancelation for file -- quit and move on
            if not proceed:
                CLI_LOGGER.warning(f"File: '{cpath}' -- cancelled "
                                   "-- moving on to next file")
                continue

            # Start file processing -- compression, encryption, etc.
            pools[pool_executor.submit(
                delivery.prep_upload,
                cpath,
                delivery.data[cpath])
            ] = cpath

        # DELIVER FILES -- UPLOAD TO S3
        # When file processing is done -- move on to upload
        for pfuture in as_completed(pools):
            ppath = pools[pfuture]      # Original file path -- keep track
            processed, efile, esize, \
                ds_compressed, error = pfuture.result()     # Get info

            # Update file info
            delivery.update_delivery(file=ppath,
                                     updinfo={'proceed': processed,
                                              'encrypted_file': efile,
                                              'encrypted_size': esize,
                                              'ds_compressed': ds_compressed,
                                              'error': error})
            # Set file processing as finished
            delivery.set_progress(item=ppath, processing=True, finished=True)
            # CLI_LOGGER.debug(f"File: {ppath}, Info: {delivery.data[ppath]}")

            # If DS noted cancelation for file -- quit and move on
            if not processed:
                CLI_LOGGER.warning(f"File: '{ppath}' -- cancelled "
                                   "-- moving on to next file")
                continue

            # Start file delivery -- upload to S3
            uthreads[
                thread_executor.submit(delivery.put,
                                       file=ppath,
                                       fileinfo=delivery.data[ppath])
            ] = ppath

        # FINISH DELIVERY
        # When file upload is done -- set as finished
        for ufuture in as_completed(uthreads):
            upath = uthreads[ufuture]       # Original file path -- keep track
            uploaded, error = ufuture.result()     # Get info

            # Update file info
            delivery.update_delivery(file=upath,
                                     updinfo={'proceed': uploaded,
                                              'error': error})
            # Set file upload as finished
            delivery.set_progress(item=upath, upload=True, finished=True)
            # CLI_LOGGER.debug(f"File: {upath}, Info: {delivery.data[upath]}")

            # If DS noted cancelation for file -- quit and move on
            if not uploaded:
                CLI_LOGGER.warning(f"File: '{upath}' -- cancelled "
                                   "-- moving on to next file")
                continue
            CLI_LOGGER.info(f"File: {upath} -- DELIVERED")

            delivery.set_progress(item=upath, db=True, started=True)
            # DATABASE UPDATE TO BE THREADED LATER
            # CURRENTLY PROBLEMS WITH COUCHDB
            try:
                with DatabaseConnector('project_db') as project_db:
                    _project = project_db[delivery.project_id]
                    keyinfo = delivery.data[upath]
                    key = str(keyinfo['new_file'])
                    dir_path = str(keyinfo['directory_path'])

                    _project['files'][key] = \
                        {"directory_path": dir_path,
                            "size": keyinfo['size'],
                            "ds_compressed": keyinfo['ds_compressed'],
                            "date_uploaded": timestamp()}
                    project_db.save(_project)
            except Exception as e:  # FIX EXCEPTION HERE
                emessage = f"Could not update database: {e}"
                CLI_LOGGER.warning(emessage)
            else:
                CLI_LOGGER.info("Upload completed!"
                                f"{delivery.data[upath]}")
            delivery.set_progress(item=upath, db=True, finished=True)

        # POOLEXECUTORS STOPPED ####################### POOLEXECUTORS STOPPED #
        pool_executor.shutdown(wait=True)
        thread_executor.shutdown(wait=True)

###############################################################################
# GET ################################################################### GET #
###############################################################################


@cli.command()
@click.option('--config', '-c',
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
def get(config: str, username: str, password: str, project: str,
        pathfile: str, data: tuple):
    """Downloads the files from S3 bucket. Not usable by facilities. """

    with DataDeliverer(config=config, username=username, password=password,
                       project_id=project, pathfile=pathfile, data=data) \
            as delivery:

        recip_pub = delivery.get_recipient_key(keytype="public")
        recip_secret = delivery.get_recipient_key(keytype="private")

        # Create multithreading pool
        with concurrent.futures.ThreadPoolExecutor() as thread_executor:
            download_threads = []
            for path in delivery.data:

                # Download all files
                t_future = thread_executor.submit(delivery.get, path)
                download_threads.append(t_future)

            with concurrent.futures.ProcessPoolExecutor() as pool_exec:
                pools = []
                for f in concurrent.futures.as_completed(download_threads):
                    downloaded = f.result()[0]
                    down_path = f.result()[1]

                    for p in delivery.data[down_path]:
                        sender_pub = delivery.get_recipient_key(
                            keytype="fac_public")
                        p_future = pool_exec.submit(finish_download,
                                                    p, recip_secret, sender_pub)

                        pools.append(p_future)
                        # p_future = pool_exec.submit(gen_hmac, p)
                        # pools.append(p_future)

                    for p in concurrent.futures.as_completed(pools):
                        print(p.result())
