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
from code_api.crypt4gh.crypt4gh import lib, header, keys

from code_api.data_deliverer import DataDeliverer, DatabaseConnection, \
    timestamp, finish_download
from code_api.dp_crypto import Crypt4GHKey
from code_api.dp_exceptions import DataException

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
                       pathfile=pathfile, data=data) \
            as delivery:

        # Generate public key pair
        key = Crypt4GHKey()

        # Create multiprocess pool
        with concurrent.futures.ProcessPoolExecutor() as pool_exec:
            pools = []                  # Ongoing pool operations
            file_dict = {}              # Information about each path
            for path in delivery.data:
                if not isinstance(path, Path):
                    raise OSError(f"The specified path {path} "
                                  "was not recognized. Delivery Portal error.")

                if not path.is_dir() and not path.is_file():
                    raise OSError(f"Path type {path} not identified."
                                  "Have you entered the correct path?")

                if path.is_dir():           # If the path is a folder
                    path_base = path.name   # The folders name
                    all_dirs = list(path.glob('**'))    # All subfolders
                    for dir_ in all_dirs:
                        all_files = [f for f in dir_.glob('*') if f.is_file()
                                     and "DS_Store" not in str(f)]  # <- delete
                        for file in all_files:  # Upload all files
                            path_from_base = delivery.get_bucket_path(
                                file=file,
                                path_base=path_base
                            )

                            # Prepare files for upload incl hashing and
                            # encryption
                            p_future = pool_exec.submit(
                                key.prep_upload,
                                file,
                                recip_key.pubkey,
                                delivery.tempdir,
                                path_from_base
                            )

                            pools.append(p_future)
                            file_dict[file] = {"path_base": path_base,
                                               "hash": "",
                                               "bucket_path": path_from_base}
                elif path.is_file():
                    path_from_base = delivery.get_bucket_path(file=path)

                    # get recipient public key
                    recip_pub = delivery.get_recipient_key()

                    # Prepare files for upload incl hashing etc
                    p_future = pool_exec.submit(key.prep_upload,
                                                path,
                                                recip_pub,
                                                delivery.tempdir,
                                                path_from_base)
                    pools.append(p_future)
                    file_dict[path] = {"path_base": None,
                                       "hash": "",
                                       "bucket_path": path_from_base}

            # Create multithreading pool
            with concurrent.futures.ThreadPoolExecutor() as thread_exec:
                upload_threads = []
                # When the pools are finished
                # for f in concurrent.futures.as_completed(pools):
                for f in concurrent.futures.as_completed(pools):
                    # save file hash in dict
                    prep_result = f.result()
                    o_f = prep_result[0]  # original file
                    file_dict[o_f]["encrypted"] = prep_result[1]
                    file_dict[o_f]["hash"] = prep_result[2]

                    # begin upload
                    t_future = thread_exec.submit(
                        delivery.put,
                        file_dict[o_f]['encrypted'],
                        file_dict[o_f]['path_base'],
                        o_f
                    )
                    upload_threads.append(t_future)

                for t in concurrent.futures.as_completed(upload_threads):
                    upload_result = t.result()
                    o_f_u = upload_result[0]  # original file
                    if o_f_u not in file_dict:
                        raise DataException("ERROR! File not recognized.")

                    if file_dict[o_f_u]['encrypted'] \
                            != upload_result[1]:
                        raise DataException("Encrypted file path not recorded "
                                            "for original, entered path.")

                    file_dict[o_f_u]['uploaded'] = upload_result[2]
                    file_dict[o_f_u]['bucket_path'] = upload_result[3]
                    file_dict[o_f_u]['message'] = upload_result[4]

                    if file_dict[o_f_u]['uploaded'] \
                            and "ERROR" not in file_dict[o_f_u]['message']:
                        # update database here
                        with DatabaseConnection('project_db') as project_db:
                            _project = project_db[delivery.project_id]
                            _project['files'][file_dict[o_f_u]['bucket_path']] \
                                = {"size": upload_result[1].stat().st_size,
                                   "mime": "",
                                   "date_uploaded": timestamp(),
                                   "checksum": file_dict[o_f_u]['hash']}
                            _project['project_keys']['fac_public'] = key.pubkey.hex()
                            project_db.save(_project)

        print("\n----DELIVERY COMPLETED----\n"
              "The following files were uploaded: ")
        for fx in file_dict:
            if file_dict[fx]['uploaded']:
                print(fx)

        print("\nThe following files were NOT uploaded: ")
        for n_u in file_dict:
            if not file_dict[n_u]['uploaded']:
                if file_dict[n_u]['message'] == "exists":
                    print(f"File already in bucket:\t{n_u}")
                elif "ERROR" in file_dict[n_u]['message']:
                    print(f"Upload failed:\t{n_u}\t"
                          f"{file_dict[n_u]['message']}")

        print()


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
                if isinstance(path, str):
                    # Download all files
                    t_future = thread_exec.submit(delivery.get, path)
                    download_threads.append(t_future)

            with concurrent.futures.ProcessPoolExecutor() as pool_exec:
                pools = []
                for f in concurrent.futures.as_completed(download_threads):
                    print(f.result())
                    sender_pub = delivery.get_recipient_key(
                        keytype="fac_public")
                    print("Sender public key: ", sender_pub)
                    p_future = pool_exec.submit(finish_download,
                                                f.result(), recip_secret, sender_pub)

                    pools.append(p_future)
                    # p_future = pool_exec.submit(gen_hmac, f.result())
                    # pools.append(p_future)

                for p in concurrent.futures.as_completed(pools):
                    print(p.result())
