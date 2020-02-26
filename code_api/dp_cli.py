"""
Command line interface for Data Delivery Portal
"""

# IMPORTS ############################################################ IMPORTS #

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

# CONFIG ############################################################## CONFIG #

logging.config.dictConfig({
    'version': 1,
    'disable_existing_loggers': False,
})


# GLOBAL VARIABLES ########################################## GLOBAL VARIABLES #

COMPRESSED_FORMATS = dict()


# MAIN ################################################################## MAIN #

@click.group()
def cli():
    global COMPRESSED_FORMATS
    

@cli.command()
@click.option('--config', '-c',
              required=False,
              type=click.Path(exists=True),
              help="Path to config file containing e.g. username, password, project id, etc.")
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
              help="Path to file containing all files and folders to be uploaded.")
@click.option('--data', '-d',
              required=False,
              type=click.Path(exists=True),
              multiple=True,
              help="Path to file or folder to upload.")
def put(config: str, username: str, password: str, project: str,
        owner: str, pathfile: str, data: tuple) -> (str):
    """Uploads the files to S3 bucket. Only usable by facilities. """

    with DataDeliverer(config=config, username=username, password=password,
                       project_id=project, project_owner=owner, pathfile=pathfile, data=data) as delivery:
        delivery.put()

        # print(f"{delivery.method}, {delivery.project_id}, {delivery.project_owner}, "
        #       f"\n{delivery.user.username}, {delivery.user.password}, {delivery.user.id}")
        # print(f"{delivery.tempdir},\n {delivery.s3.resource}, {delivery.s3.project}, {delivery.s3.bucket}, {delivery.s3.bucket.name}")


@cli.command()
@click.option('--config', '-c',
              required=False,
              type=click.Path(exists=True),
              help="Path to config file containing e.g. username, password, project id, etc.")
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
              help="Path to file containing all files and folders to be uploaded.")
@click.option('--data', '-d',
              required=False,
              multiple=True,
              type=str,
              help="Path to file or folder to upload.")
def get(config: str, username: str, password: str, project: str,
        pathfile: str, data: tuple):
    """Downloads the files from S3 bucket. Not usable by facilities. """

    pass
    # all_files = list()

    # user_info = verify_user_input(config=config,
    #                               username=username,
    #                               password=password,
    #                               project=project)

    # user_id, s3_proj = check_access(login_info=user_info)

    # if not isinstance(user_id, str):
    #     raise DeliveryPortalException("User ID not set, "
    #                                   "cannot proceed with data delivery.")

    # all_files = collect_all_data(data=data, pathfile=pathfile)

    # # This should never be able to be true - just precaution
    # if not all_files:
    #     raise DeliveryPortalException("Data tuple empty. Nothing to upload."
    #                                   "Cancelling delivery.")

    # # Create temporary folder with timestamp and all subfolders
    # timestamp = get_current_time().replace(" ", "_").replace(":", "-")
    # temp_dir = f"{os.getcwd()}/DataDelivery_{timestamp}"
    # dirs = tuple(
    #     f"{temp_dir}/{sf}" for sf in ["", "files/", "keys/", "meta/", "logs/"])

    # dirs_created = create_directories(dirs=dirs, temp_dir=temp_dir)
    # if not dirs_created:  # If error when creating one of the folders
    #     pass    # raise exception here

    # s3_resource, project_bucket = get_s3_info(current_project=user_info['project'],
    #                                           s3_proj=s3_proj)

    # # Create multithreading pool
    # with concurrent.futures.ThreadPoolExecutor() as executor:
    #     upload_threads = []
    #     for path in all_files:
    #         if type(path) == str:
    #             # Download all files
    #             future = executor.submit(s3_download, path,
    #                                      s3_resource, project_bucket, f"{temp_dir}/files/{path}")
    #             upload_threads.append(future)

    #     for f in concurrent.futures.as_completed(upload_threads):
    #         print(f.result())
