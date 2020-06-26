"""
Command line interface for Data Delivery System
"""

# IMPORTS ########################################################### IMPORTS #

import concurrent.futures
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

# CONFIG ############################################################# CONFIG #

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


# GLOBAL VARIABLES ######################################### GLOBAL VARIABLES #


COMPRESSED_FORMATS = dict()

# MAIN ################################################################# MAIN #


@click.group()
def cli():
    global COMPRESSED_FORMATS


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
def put(config: str, username: str, password: str, project: str,
        owner: str, pathfile: str, data: tuple) -> (str):
    """Uploads the files to S3 bucket. Only usable by facilities. """

    # Create DataDeliverer to handle files and folders
    with DataDeliverer(config=config, username=username, password=password,
                       project_id=project, project_owner=owner,
                       pathfile=pathfile, data=data) as delivery:

        # Setup logging
        CLI_LOGGER = config_logger(LOG_FILE)
        CLI_LOGGER.info(f"Data to deliver: {delivery.data}\n"
                        f"Number of items to upload: {len(delivery.data)}")

        # Create multiprocess pool
        with concurrent.futures.ProcessPoolExecutor() as pool_executor:
            CLI_LOGGER.debug("Started ProcessPoolExecutor...")

            pools = []                  # Ongoing pool operations
            for path in delivery.data:  # Iterate through all files

                CLI_LOGGER.debug(f"Beginning delivery of {path}")

                proceed = delivery.get_content_info(item=path)

                CLI_LOGGER.debug(f"Proceed to processing: {proceed}")
                if not proceed or not delivery.data[path]['proceed']:
                    CLI_LOGGER.debug("Moving on to next file")
                    continue

                CLI_LOGGER.debug(f"proceed: {proceed} --> {path}")

                p_future = pool_executor.submit(
                    fh.prep_upload,
                    path,
                    delivery.data[path],
                    delivery.tempdir.files
                )

                CLI_LOGGER.info(f"Started processing {path}...")
                # # Add to pool list and update file info
                pools.append(p_future)
                CLI_LOGGER.info(f"Updated data dictionary. "
                                f"{path}: {delivery.data[path]}")

            # Create multithreading pool
            with concurrent.futures.ThreadPoolExecutor() as thread_exec:
                upload_threads = []
                # When the pools are finished
                for f in concurrent.futures.as_completed(pools):

                    success, opath, (epath, esize, compressed, error), \
                        message = f.result()
                    CLI_LOGGER.debug(f"prepped: {success}, \n{opath}, \n"
                                     f"{epath}, \n{esize}, \n{compressed}, "
                                     f"\n{error}, \n{message}")

                    updated = delivery.update_data_dict(
                        path=opath,
                        pathinfo={
                            'success': success,
                            'encrypted_file': epath,
                            'encrypted_size': esize,
                            'compressed': compressed,
                            'error': error,
                            'message': message
                        }
                    )
                    if not updated:
                        CLI_LOGGER.exception("Data info dictionary failed"
                                             " to be updated, cannot proceed"
                                             f" with delivery of '{opath}'")
                        continue
                    if not delivery.data[opath]['proceed']:
                        continue

                    # begin upload
                    t_future = thread_exec.submit(
                        delivery.put,
                        opath
                    )

                    upload_threads.append(t_future)

                for t in concurrent.futures.as_completed(upload_threads):
                    uploaded, ofile, ufile, bucketpath, error = t.result()
                    CLI_LOGGER.debug(f"{uploaded}, {ofile}, {ufile}")

                    if ofile not in delivery.data:
                        CLI_LOGGER.exception("File not recognized.")
                        continue

                    if delivery.data[ofile]['encrypted_file'] \
                            != ufile:
                        emessage = (" Encrypted file path not recorded"
                                    " for original, entered path.")
                        CLI_LOGGER.exception(emessage)
                        error = error + emessage

                    delivery.update_data_dict(
                        path=ofile,
                        pathinfo={'success': uploaded,
                                  'error': error}
                    )

                    if not uploaded or not delivery.data[ofile]['proceed']:
                        CLI_LOGGER.warning("Upload failed, continuing to next file - "
                                           f"file: {original_file} "
                                           f"({uploaded_file})")
                        continue
                    else:
                        CLI_LOGGER.debug("Beginning database update. "
                                         f"{ofile}")
                        # update database here
                        with DatabaseConnector('project_db') as project_db:
                            _project = project_db[delivery.project_id]
                            # str(ufile).partition(
                            # str(filedir))[-1]
                            # ADD CHECK IF EXISTS IN DB - BEFORE UPLOAD?
                            _project['files'][str(delivery.data[ofile]['new_file'].name)] = \
                                {"directory_path": str(delivery.data[ofile]['directory_path']),
                                 "size": delivery.data[ofile]['size'],
                                 "compressed": delivery.data[ofile]['compressed'],
                                 "date_uploaded": timestamp()}
                            project_db.save(_project)

                        CLI_LOGGER.info("Upload completed!"
                                        f"{delivery.data[ofile]}")
                        delivery.data[ofile]["success"] = True
                        CLI_LOGGER.debug(
                            "success: "
                            f"{delivery.data[ofile]['success']}"
                        )


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
        with concurrent.futures.ThreadPoolExecutor() as thread_exec:
            download_threads = []
            for path in delivery.data:

                # Download all files
                t_future = thread_exec.submit(delivery.get, path)
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
