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

from cli_code.data_deliverer import DataDeliverer, \
    timestamp, finish_download
from cli_code.crypto_ds import Crypt4GHKey
from cli_code.exceptions_ds import DataException
from cli_code.database_connector import DatabaseConnector
from cli_code.s3_connector import S3Object

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

        # Generate public key pair
        key = Crypt4GHKey()

        # Create multiprocess pool
        with concurrent.futures.ProcessPoolExecutor() as pool_exec:
            pools = []                  # Ongoing pool operations
            for path in delivery.data:
                if not delivery.data[path]:
                    raise OSError(f"Path type {path} not identified."
                                  "Have you entered the correct path?")

                filedir = delivery.tempdir[1]
                # If the specified path was a folder
                if delivery.data[path]['path_base'] is not None:
                    # Create folder in temporary dir
                    try:
                        original_umask = os.umask(0)
                        filedir = filedir / \
                            delivery.data[path]['path_base']
                        if not filedir.exists():
                            filedir.mkdir(parents=True)
                    except IOError as ioe:
                        sys.exit(f"Could not create folder {filedir}: {ioe}")
                    finally:
                        os.umask(original_umask)

                # Path from folder to file
                path_from_base = delivery.get_bucket_path(
                    file=path,
                    path_base=delivery.data[path]['path_base']
                )
                    
                exists = delivery.s3.file_exists_in_bucket(
                    str(path_from_base / Path(path.name)))

                if exists:
                    delivery.data[path].update({"Error": "Exists"})
                    continue  # moves on to next file

                # Get recipient public key
                recip_pub = delivery.get_recipient_key()

                # Prepare files for upload incl hashing and encryption
                p_future = pool_exec.submit(key.prep_upload,
                                            path,
                                            recip_pub,
                                            filedir,
                                            path_from_base)

                pools.append(p_future)  # Add to pool list
                delivery.data[path].update({"path_from_base": path_from_base})

            # Create multithreading pool
            with concurrent.futures.ThreadPoolExecutor() as thread_exec:
                upload_threads = []
                # When the pools are finished
                for f in concurrent.futures.as_completed(pools):
                    # save file hash in dict
                    original_file = f.result()[0]
                    encrypted_file = f.result()[1]
                    checksum = f.result()[2]

                    if encrypted_file == "Error":
                        # If the encryption failed, the checksum is an exception
                        delivery.data[original_file]["Error"] = checksum
                    else:
                        delivery.data[original_file].update(
                            {"encrypted": encrypted_file,
                             "hash": checksum}
                        )

                    # begin upload
                    t_future = thread_exec.submit(
                        delivery.put,
                        delivery.data[original_file]['encrypted'],
                        delivery.data[original_file]['path_from_base'],
                        original_file
                    )
                    upload_threads.append(t_future)

                for t in concurrent.futures.as_completed(upload_threads):
                    original_file_ = t.result()[0]
                    uploaded_file = t.result()[1]
                    success = t.result()[2]
                    bucket_path = t.result()[3]

                    if original_file_ not in delivery.data:
                        raise DataException("ERROR! File not recognized.")

                    if delivery.data[original_file_]['encrypted'] \
                            != uploaded_file:
                        raise DataException("Encrypted file path not recorded "
                                            "for original, entered path.")

                    if not success:
                        # If upload failed, bucket_path is an error message
                        delivery.data[original_file_].update(
                            {"success": False,
                             "Error": bucket_path}
                        )
                    elif success:
                        # update database here
                        with DatabaseConnector('project_db') as project_db:
                            _project = project_db[delivery.project_id]
                            _project['files'][str(delivery.data[original_file_]['path_from_base'])] = \
                                {"size": original_file_.stat().st_size,
                                 "mime": "",
                                 "date_uploaded": timestamp(),
                                 "checksum": delivery.data[original_file_]['hash']}
                            _project['project_keys']['fac_public'] = key.pubkey.hex()
                            project_db.save(_project)
                        delivery.data[original_file_]["success"] = True
                    else:
                        raise Exception("The upload did not return boolean, "
                                        "cannot determine if delivery successful!")

        
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
