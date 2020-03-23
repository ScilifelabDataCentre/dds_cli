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

from code_api.data_deliverer import DataDeliverer
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

    recip_keys = Crypt4GHKey()
    print(f"\nRecipient public key: {recip_keys.public}\n"
          f"Recipient public key, parsed: {recip_keys.public_parsed}\n"
          f"Recipient private key: {recip_keys.secret}\n"
          f"Recipient private key, decrypted: {recip_keys.secret_decrypted}\n")
    keys = Crypt4GHKey()
    print(f"\nSender public key: {keys.public}\n"
          f"Sender public key, parsed: {keys.public_parsed}\n"
          f"Sender private key: {keys.secret}\n"
          f"Sender private key, decrypted: {keys.secret_decrypted}\n")

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
                                keys.prep_upload,
                                file,
                                recip_keys.public_parsed,
                                delivery.tempdir,
                                path_from_base
                            )

                            pools.append(p_future)
                            file_dict[file] = {"path_base": path_base,
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
                        pass
                        # update database here

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

    recip_keys = Crypt4GHKey()
    sender_keys = Crypt4GHKey()

    recip_keys.public = b'-----BEGIN CRYPT4GH PUBLIC KEY-----\n+XuYOw8pawjCRQaHTXPY9b4730N4ex21vqTnedaLIC8=\n-----END CRYPT4GH PUBLIC KEY-----\n'
    recip_keys.public_parsed = b'\xf9{\x98;\x0f)k\x08\xc2E\x06\x87Ms\xd8\xf5\xbe;\xdfCx{\x1d\xb5\xbe\xa4\xe7y\xd6\x8b /'
    recip_keys.secret = b'-----BEGIN CRYPT4GH PRIVATE KEY-----\nYzRnaC12MQAGc2NyeXB0ABQAAAAAepEiIg+NeDjLp5yE9V98rAARY2hhY2hhMjBfcG9seTEzMDUAPE+akuodTEJbxn4oaNoYvbO/W8A1jKH4M5pY+ij+kX+nKz8oJP+BAq+WBwynskwNhvZFOUbgOYu5uFlQvQ==\n-----END CRYPT4GH PRIVATE KEY-----\n'
    recip_keys.secret_decrypted = b'\x86W\\\x19\xda\xa5\xeb\xc5\x988\x9e\xef&\xdc&\x1f^\xd1O\xf3\xfa\xea\xa4\x14\xcd\xc4"\xcf\x0f\xe8\x83\x14'

    sender_keys.public = b'-----BEGIN CRYPT4GH PUBLIC KEY-----\nMYi1iAbrtJnpOmLbKRVpt3soZ+OSOVyESlkRxqkrXG8=\n-----END CRYPT4GH PUBLIC KEY-----\n'
    sender_keys.public_parsed = b'1\x88\xb5\x88\x06\xeb\xb4\x99\xe9:b\xdb)\x15i\xb7{(g\xe3\x929\\\x84JY\x11\xc6\xa9+\\o'
    sender_keys.secret = b'-----BEGIN CRYPT4GH PRIVATE KEY-----\nYzRnaC12MQAGc2NyeXB0ABQAAAAAns6OpLk5MjEAnE++eR3/xQARY2hhY2hhMjBfcG9seTEzMDUAPBJN4e5i+WOuqLDGfs4fuzzfxndBbpq6copPvVAM7reKHxralQFoVUCAIEEfbMHGo/vKUAGr7ONUI5cJDQ==\n-----END CRYPT4GH PRIVATE KEY-----\n'
    sender_keys.secret_decrypted = b'\xd4\x1e\xef\x9a~\xe6\x8b\xd8\xe6\xc3\xec\xaeI\x9e9\x03B\xb4\xf4\x16\xc5\xac=YMJV\x0cv\xd3\x89N'

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
                    print(f.result())

                    p_future = pool_exec.submit(recip_keys.finish_download,
                                                f.result(), sender_keys)

                    pools.append(p_future)
                    # p_future = pool_exec.submit(gen_hmac, f.result())
                    # pools.append(p_future)

                for p in concurrent.futures.as_completed(pools):
                    print(p.result())
