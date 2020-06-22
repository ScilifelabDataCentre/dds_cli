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
        CLI_LOGGER.info(f"Number of files to upload: {len(delivery.data)}")

        # Create multiprocess pool
        with concurrent.futures.ProcessPoolExecutor() as pool_executor:
            CLI_LOGGER.debug("Started ProcessPoolExecutor...")

            pools = []                  # Ongoing pool operations
            for path in delivery.data:  # Iterate through all files

                CLI_LOGGER.debug(f"Beginning delivery of {path}")

                proceed = delivery.get_content_info(item=path)

                if not proceed:
                    CLI_LOGGER.warning("One or more of the file/directory "
                                       f"{path} contents has/have already "
                                       "been uploaded to the assigned "
                                       "S3 project bucket. Not uploading "
                                       "the specified path.")
                    delivery.data[path].update(
                        {"error": "Exists"}
                    )
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
                CLI_LOGGER.debug(f"Updated data dictionary. "
                                 f"{path}: {delivery.data[path]}")

            for f in concurrent.futures.as_completed(pools):
                print(f.result())

            # Create multithreading pool
            # with concurrent.futures.ThreadPoolExecutor() as thread_exec:
            #     upload_threads = []
                # When the pools are finished
                # for f in concurrent.futures.as_completed(pools):
                #     CLI_LOGGER.debug(f.result())
                # CLI_LOGGER.debug(f.result())
                #     original_file = f.result()[0]
                #     encrypted_file = f.result()[1]
                #     e_size = f.result()[2]  # Encrypted file size
                #     compressed = f.result()[3]  # Boolean
                #     CLI_LOGGER.debug("Completed pool future---"
                #                      f"Original file: {original_file}"
                #                      f"-- size: {delivery.data[original_file]['size']}, "
                #                      f"Encrypted file: {encrypted_file}"
                #                      f"-- size: {e_size}, "
                #                      f"Compressed? {compressed}")

                #     if encrypted_file == "Error":
                #         CLI_LOGGER.exception(f"Encryption failed! -- {e_size}")
                #         # If the encryption failed, the e_size is an exception
                #         delivery.data[original_file]["Error"] = e_size
                #     else:
                #         delivery.data[original_file].update(
                #             {"original_size": delivery.data[original_file]['size'],
                #              "compressed": compressed,
                #              "encrypted": encrypted_file,
                #              "encrypted_size": e_size,
                #              "hash": "haven't fixed this yet"}
                #         )
                #         CLI_LOGGER.debug("Updated data dictionary! \n"
                #                          f"{original_file}: "
                #                          f"{delivery.data[original_file]}")

                #     # begin upload
                #     t_future = thread_exec.submit(
                #         delivery.put,
                #         delivery.data[original_file]['encrypted'],
                #         delivery.data[original_file]['directory_path'],
                #         original_file
                #     )
                #     CLI_LOGGER.debug(
                #         f"Upload of {original_file} "
                #         f"({delivery.data[original_file]['encrypted']})"
                #         "started."
                #     )
                #     upload_threads.append(t_future)

                # for t in concurrent.futures.as_completed(upload_threads):
                #     original_file_ = t.result()[0]
                #     uploaded_file = t.result()[1]
                #     success = t.result()[2]
                #     directory_path = t.result()[3]
                #     CLI_LOGGER.debug("Completed thread future---"
                #                      f"Original file: {original_file}, "
                #                      f"Uploaded file: {uploaded_file}, "
                #                      f"Successful? {success}, "
                #                      f"Directory path: {directory_path}")

                #     if original_file_ not in delivery.data:
                #         CLI_LOGGER.exception("File not recognized.")

                #     if delivery.data[original_file_]['encrypted'] \
                #             != uploaded_file:
                #         CLI_LOGGER.exception("Encrypted file path not recorded"
                #                              " for original, entered path.")

                #     if not isinstance(success, bool):
                #         CLI_LOGGER.exception("The upload did not return "
                #                              "boolean, cannot determine if "
                #                              "delivery successful!")
                #     if not success:
                #         CLI_LOGGER.warning("Upload failed - "
                #                            f"file: {original_file} "
                #                            f"({uploaded_file})")
                #         # If upload failed, directory_path is an error message
                #         delivery.data[original_file_].update(
                #             {"success": False,
                #              "Error": directory_path}
                #         )
                #         continue
                #     else:
                #         CLI_LOGGER.debug("Beginning database update. "
                #                          f"{original_file}")
                #         # update database here
                #         with DatabaseConnector('project_db') as project_db:
                #             _project = project_db[delivery.project_id]
                #             file_path = str(uploaded_file).partition(
                #                 str(filedir))[-1]
                #             # ADD CHECK IF EXISTS IN DB - BEFORE UPLOAD?
                #             _project['files'][uploaded_file.name] = {"full_path": file_path,
                #                                                      "size": original_file_.stat().st_size,
                #                                                      "mime": "",
                #                                                      "date_uploaded": timestamp(),
                #                                                      "checksum": delivery.data[original_file_]['hash']}
                #             project_db.save(_project)
                #         CLI_LOGGER.debug(
                #             "Database updated -- \n"
                #             f"full_path: {file_path}, "
                #             f"size: {original_file_.stat().st_size}, "
                #             f"mime: '', "
                #             f"date_uploaded: {timestamp()}, "
                #             "checksum: "
                #             f"{delivery.data[original_file_]['hash']}"
                #         )

                #         CLI_LOGGER.info("Upload completed!"
                #                         f"{delivery.data[original_file_]}")
                #         delivery.data[original_file_]["success"] = True
                #         CLI_LOGGER.debug(
                #             "success: "
                #             f"{delivery.data[original_file_]['success']}"
                #         )


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
