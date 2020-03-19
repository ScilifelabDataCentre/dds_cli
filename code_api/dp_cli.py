"""
Command line interface for Data Delivery Portal
"""

# IMPORTS ########################################################### IMPORTS #

import concurrent.futures
import logging
import logging.config
from pathlib import Path
import sys

import click
from crypt4gh import lib, header, keys
from code_api.crypt4gh.crypt4gh.lib import encrypt
import tqdm

from code_api.data_deliverer import DataDeliverer
from code_api.dp_crypto import gen_hmac
from code_api.dp_crypto import Crypt4GHKey

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

    recip_keys = Crypt4GHKey()
    keys = Crypt4GHKey()

    # Create DataDeliverer to handle files and folders
    with DataDeliverer(config=config, username=username, password=password,
                       project_id=project, project_owner=owner,
                       pathfile=pathfile, data=data) \
            as delivery:

        # Create multiprocess pool
        with concurrent.futures.ProcessPoolExecutor() as pool_exec:
            pools = []                  # Ongoing pool operations
            file_dict = {}              # Information about each path
            for path in delivery.data:
                if isinstance(path, Path):
                    if path.is_dir():           # If the path is a folder
                        path_base = path.name   # The folders name
                        all_dirs = list(path.glob('**'))    # All subfolders
                        for dir_ in all_dirs:
                            all_files = [f for f in dir_.glob('*')  # All files
                                         if f.is_file()
                                         and "DS_Store" not in str(f)]  # del
                            for file in all_files:  # Upload all files
                                path_from_base = \
                                    delivery.get_bucket_path(
                                        file=file,
                                        path_base=path_base
                                    )

                                # Prepare files for upload incl hashing and
                                # encryption
                                p_future = \
                                    pool_exec.submit(keys.prep_upload,
                                                     file,
                                                     recip_keys.public_parsed,
                                                     delivery.tempdir,
                                                     path_from_base)
                                pools.append(p_future)
                                file_dict[file] = \
                                    {"path_base": path_base,
                                     "hash": "",
                                     "bucket_path": path_from_base}
                    elif path.is_file():
                        path_from_base = delivery.get_bucket_path(file=path)

                        # Prepare files for upload incl hashing etc
                        p_future = pool_exec.submit(keys.prep_upload,
                                                    path,
                                                    recip_keys.public_parsed,
                                                    delivery.tempdir,
                                                    path_from_base)
                        pools.append(p_future)
                        file_dict[path] = {"path_base": None,
                                           "hash": "",
                                           "bucket_path": path_from_base}

                    else:
                        raise OSError(f"Path type {path} not identified."
                                      "Have you entered the correct path?")
                else:
                    raise OSError(f"The specified path {path} "
                                  "was not recognized. Delivery Portal error.")

            # Create multithreading pool
            with concurrent.futures.ThreadPoolExecutor() as thread_exec:
                upload_threads = []
                # When the pools are finished
                # for f in concurrent.futures.as_completed(pools):
                for f in concurrent.futures.as_completed(pools):
                    print(f.result())
                    # save file hash in dict
                    orig_file = f.result()[0]
                    file_dict[orig_file]["encrypted"] = f.result()[1]
                    file_dict[orig_file]["hash"] = f.result()[2]

                    # begin upload
                    t_future = thread_exec.submit(
                        delivery.put,
                        file_dict[orig_file]['encrypted'],
                        file_dict[orig_file]['bucket_path']
                    )
                    upload_threads.append(t_future)

                for t in concurrent.futures.as_completed(upload_threads):
                    print(t.result())


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
        # Create multithreading pool
        with concurrent.futures.ThreadPoolExecutor() as thread_exec:
            download_threads = []
            for path in delivery.data:
                if isinstance(path, str):
                    # Download all files
                    t_future = thread_exec.submit(delivery.get, path)
                    download_threads.append(t_future)

            with concurrent.futures.ProcessPoolExecutor() as pool_exec:
                pools = []
                for f in concurrent.futures.as_completed(download_threads):
                    p_future = pool_exec.submit(gen_hmac, f.result())
                    pools.append(p_future)

                for p in concurrent.futures.as_completed(pools):
                    print(p.result())
