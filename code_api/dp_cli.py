"""
Command line interface for Data Delivery Portal
"""

# IMPORTS ########################################################### IMPORTS #

from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from cryptography.hazmat.primitives import hashes, hmac
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
import shutil
import zipfile
import zlib
import tarfile
import gzip
import json

from pathlib import Path
import tempfile

import click
import couchdb
import sys
import hashlib
import os
import filetype
import mimetypes
from typing import Union

import datetime
from itertools import chain
import logging
import logging.config

from ctypes import *

from crypt4gh import lib, header, keys
from functools import partial
from getpass import getpass

from code_api.dp_exceptions import *
from botocore.exceptions import ClientError

import boto3
from boto3.s3.transfer import TransferConfig
import smart_open

import concurrent.futures

import time
import traceback

from code_api.datadel_s3 import S3Object
from code_api.data_deliverer import DataDeliverer, DPUser
from code_api.dp_crypto import gen_hmac

from tqdm_multi_thread import TqdmMultiThreadFactory

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
        # Create multithreading pool
        with concurrent.futures.ThreadPoolExecutor() as executor:
            upload_threads = []
            for path in delivery.data:
                if isinstance(path, Path):
                    # check if folder and then get all subfolders
                    if path.is_dir():
                        path_base = path.name
                        all_dirs = list(path.glob('**'))  # all (sub)dirs
                        for dir_ in all_dirs:
                            # check which files are in the directory
                            all_files = \
                                [f for f in dir_.glob('*') if f.is_file()]
                            for file in all_files:  # Upload all files
                                # checksum = executor.submit(gen_hmac, file)
                                # upload_threads.append(checksum)

                                future = executor.submit(delivery.put,
                                                         file, path_base)
                                upload_threads.append(future)
                    elif path.is_file():
                        # checksum = executor.submit(gen_hmac, path)
                        # upload_threads.append(checksum)

                        # Upload file
                        future = executor.submit(delivery.put, path, None)
                        upload_threads.append(future)
                    else:
                        sys.exit(f"Path type {path} not identified."
                                 "Have you entered the correct path?")
                else:
                    pass  # do something, file not uploaded because not found

            for f in concurrent.futures.as_completed(upload_threads):
                print(f.result())


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
        with concurrent.futures.ThreadPoolExecutor() as executor:
            upload_threads = []
            for path in delivery.data:
                if isinstance(path, str):
                    # Download all files
                    future = executor.submit(delivery.get, path)
                    upload_threads.append(future)

            for f in concurrent.futures.as_completed(upload_threads):
                [gen_hmac(x) for x in delivery.tempdir[1].glob(
                    '**/*') if x.is_file()]
