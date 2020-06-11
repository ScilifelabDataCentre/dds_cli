"""
Command line interface for Data Delivery Portal
"""

# IMPORTS ########################################################### IMPORTS #

import concurrent.futures
import logging
import logging.config
from pathlib import Path
import sys
import os

import click
from cli_code.crypt4gh.crypt4gh import lib, header, keys

from cli_code.data_deliverer import DataDeliverer, finish_download
from cli_code.crypto_ds import Crypt4GHKey
from cli_code.database_connector import DatabaseConnector
from cli_code.exceptions_ds import DataException
import cli_code.file_handler as fh
from cli_code.s3_connector import S3Connector

# CONFIG ############################################################# CONFIG #

logging.config.dictConfig({
    'version': 1,
    'disable_existing_loggers': False,
})


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

        # Create multiprocess pool
        with concurrent.futures.ProcessPoolExecutor() as pool_exec:
            pools = []                  # Ongoing pool operations
            for path in delivery.data:  # Iterate through all files
                if not delivery.data[path]:
                    raise OSError(f"Path type {path} not identified."
                                  "Have you entered the correct path?")

                # All subfolders from entered directory to file
                directory_path = fh.get_root_path(
                    file=path,
                    path_base=delivery.data[path]['path_base']
                )

                # Check if file exists in bucket already
                exists = delivery.s3.file_exists_in_bucket(
                    str(directory_path / Path(path.name)))
                if exists:
                    delivery.data[path].update({"Error": "Exists"})
                    continue  # moves on to next file

                # Update where to save file
                filedir = fh.update_dir(
                    delivery.tempdir.files,
                    directory_path
                )

                # Prepare files for upload incl hashing and encryption
                p_future = pool_exec.submit(fh.prep_upload,
                                            path,
                                            filedir,
                                            directory_path)

                # Add to pool list and update file info
                pools.append(p_future)
                delivery.data[path].update({"directory_path": directory_path})

            # Create multithreading pool
            with concurrent.futures.ThreadPoolExecutor() as thread_exec:
                upload_threads = []
                # When the pools are finished
                for f in concurrent.futures.as_completed(pools):
                    original_file = f.result()[0]
                    o_size = f.result()[1]  # Original file size
                    encrypted_file = f.result()[2]
                    e_size = f.result()[3]  # Encrypted file size
                    compressed = f.result()[4]  # Boolean

                    if encrypted_file == "Error":
                        # If the encryption failed, the e_size is an exception
                        delivery.data[original_file]["Error"] = e_size
                    else:
                        delivery.data[original_file].update(
                            {"original_size": o_size,
                             "compressed": compressed,
                             "encrypted": encrypted_file,
                             "encrypted_size": e_size,
                             "hash": "haven't fixed this yet"}
                        )

                    # begin upload
                    t_future = thread_exec.submit(
                        delivery.put,
                        delivery.data[original_file]['encrypted'],
                        delivery.data[original_file]['directory_path'],
                        original_file
                    )
                    upload_threads.append(t_future)

                for t in concurrent.futures.as_completed(upload_threads):
                    original_file_ = t.result()[0]
                    uploaded_file = t.result()[1]
                    success = t.result()[2]
                    directory_path = t.result()[3]

                    if original_file_ not in delivery.data:
                        raise DataException("ERROR! File not recognized.")

                    if delivery.data[original_file_]['encrypted'] \
                            != uploaded_file:
                        raise DataException("Encrypted file path not recorded "
                                            "for original, entered path.")

                    if not isinstance(success, bool):
                        raise Exception("The upload did not return boolean, "
                                        "cannot determine if delivery "
                                        "successful!")
                    if not success:
                        # If upload failed, directory_path is an error message
                        delivery.data[original_file_].update(
                            {"success": False,
                             "Error": directory_path}
                        )
                        continue
                    else:
                        # update database here
                        with DatabaseConnector('project_db') as project_db:
                            _project = project_db[delivery.project_id]
                            file_path = \
                                str(uploaded_file).partition(str(filedir))[-1]
                            # ADD CHECK IF EXISTS IN DB - BEFORE UPLOAD?
                            _project['files'][uploaded_file.name] = \
                                {"full_path": file_path,
                                 "size": original_file_.stat().st_size,
                                 "mime": "",
                                 "date_uploaded": fh.timestamp(),
                                 "checksum": delivery.data[original_file_]['hash']}
                            project_db.save(_project)
                        delivery.data[original_file_]["success"] = True


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
