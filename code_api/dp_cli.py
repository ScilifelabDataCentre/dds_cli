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

from code_api.dp_exceptions import AuthenticationError, CouchDBException, \
    CompressionError, DataException, DeliveryPortalException, DeliveryOptionException, \
    EncryptionError, HashException, SecurePasswordException, StreamingError
from botocore.exceptions import ClientError

import boto3
from boto3.s3.transfer import TransferConfig
import smart_open

import concurrent.futures

import time

# CONFIG ############################################################## CONFIG #

logging.config.dictConfig({
    'version': 1,
    'disable_existing_loggers': False,
})


# GLOBAL VARIABLES ########################################## GLOBAL VARIABLES #

COMPRESSED_FORMATS = dict()


# CLASSES ############################################################ CLASSES #


# FUNCTIONS ######################################################## FUNCTIONS #

# Cryptography # # # # # # # # # # # # # # # # # # # # # # # # # Cryptography #

def secure_password_hash(password_settings: str, password_entered: str) -> (str):
    """Generates secure password hash.

    Args:
        password_settings:  String containing the salt, length of hash, n-exponential,
                            r and p variables. Taken from database. Separated by '$'.
        password_entered:   The user-specified password.

    Returns:
        str:    The derived hash from the user-specified password.

    """

    settings = password_settings.split("$")
    for i in [1, 2, 3, 4]:
        settings[i] = int(settings[i])

    kdf = Scrypt(salt=bytes.fromhex(settings[0]),
                 length=settings[1],
                 n=2**settings[2],
                 r=settings[3],
                 p=settings[4],
                 backend=default_backend())

    return (kdf.derive(password_entered.encode('utf-8'))).hex()


# Database-related # # # # # # # # # # # # # # # # # # # # # Database-related #

def couch_connect() -> (couchdb.client.Server):
    """Connects to a couchdb interface. Currently hard-coded.

    Returns:
        couchdb.client.Server:  CouchDB server instance.

    """

    try:
        couch = couchdb.Server('http://delport:delport@localhost:5984/')
    except CouchDBException as cdbe:
        sys.exit(f"Database login failed. {cdbe}")
    else:
        return couch


def get_current_time() -> (str):
    """Gets the current time. Formats timestamp.

    Returns:
        str:    Timestamp in format 'YY-MM-DD_HH-MM-SS'

    """

    now = datetime.datetime.now()
    timestamp = ""
    sep = ""

    for t in (now.year, "-", now.month, "-", now.day, " ",
              now.hour, ":", now.minute, ":", now.second):
        if len(str(t)) == 1 and isinstance(t, int):
            timestamp += f"0{t}"
        else:
            timestamp += f"{t}"

    return timestamp


# Formats # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # Formats #

def compression_dict() -> (dict):
    """Creates a dictionary of compressed types.

    Returns:
        dict:   All mime types regarded as compressed formats

    """

    extdict = mimetypes.encodings_map   # Original dict with compressed formats

    # Add custom formats
    extdict['.z'] = 'compress'
    extdict['.tgz'] = 'tar+gzip'
    extdict['.tbz2'] = 'tar+bz2'

    # Add more formats with same name as extension
    formats = ['gzip', 'lzo', 'snappy', 'zip', 'mp3', 'jpg',
               'jpeg', 'mpg', 'mpeg', 'avi', 'gif', 'png']
    for f_ in formats:
        extdict[f'.{f_}'] = f_

    return extdict


def file_type(fpath: str) -> (str, str, bool, str):
    """Guesses file mime.

    Args:
        fpath: Path to file.

    """

    mime = None             # file mime
    extension = None
    is_compressed = False
    comp_alg = None   # compression algorithm

    if os.path.isdir(fpath):
        mime = "folder"
    else:
        mime, encoding = mimetypes.guess_type(fpath)    # Guess file type
        extension = os.path.splitext(fpath)[1]          # File extension

        # Set compressed files as compressed
        if extension in COMPRESSED_FORMATS:
            is_compressed = True
            comp_alg = COMPRESSED_FORMATS[extension]

        # If the file mime type couldn't be found, manually check for ngs files
        if mime is None:
            if extension in mimetypes.types_map:
                mime = mimetypes.types_map[extension]
            elif extension == "":
                mime = None
            elif extension in (".abi", ".ab1"):
                mime = "ngs-data/abi"
            elif extension in (".embl"):
                mime = "ngs-data/embl"
            elif extension in (".clust", ".cw", ".clustal"):
                mime = "ngs-data/clustal"
            elif extension in (".fa", ".fasta", ".fas", ".fna", ".faa", ".afasta"):
                mime = "ngs-data/fasta"
            elif extension in (".fastq", ".fq"):
                mime = "ngs-data/fastq"
            elif extension in (".gbk", ".genbank", ".gb"):
                mime = "ngs-data/genbank"
            elif extension in (".paup", ".nexus"):
                mime = "ngs-data/nexus"
            else:
                mime = None
                click.echo(
                    f"Warning! Could not detect file type for file {fpath}")

        return mime, extension, is_compressed, comp_alg


# Login # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # Login #

def verify_user_input(config: str, username: str, password: str,
                      project: str, owner: str = "") -> (str, str, str):
    """Checks that the correct options and credentials are entered.

    Args:
        config:     File containing the users DP username and password,
                    and the project relating to the upload/download.
                    Can be used instead of inputing the credentials separately.
        username:   Username for DP log in.
        password:   Password connected to username.
        project:    Project ID.
        owner:      The owner of the data/project.

    Returns:
        tuple: A tuple containing three strings

            Username (str)

            Password (str)

            Project ID (str)

    """

    credentials = dict()

    # If none of username, password and config options are set
    # raise exception and quit execution -- dp cannot be accessed
    if all(x is None for x in [username, password, config]):
        raise DeliveryPortalException("Delivery Portal login credentials "
                                      "not specified. Enter: \n --username/-u "
                                      "AND --password/-pw, or --config/-c\n "
                                      "--owner/-o\n"
                                      "For help: 'dp_api --help'.")
    else:
        if owner == "":
            owner = None    # Should be a "researcher" role trying to download

        if config is not None:              # If config file entered
            if os.path.exists(config):      # and exist
                try:
                    with open(config, 'r') as cf:
                        credentials = json.load(cf)
                except OSError as ose:
                    sys.exit(f"Could not open path-file {config}: {ose}")

                credentials['owner'] = owner

                # Check that all credentials are entered and quit if not
                for c in ['username', 'password', 'project', 'owner']:
                    if c not in credentials:
                        raise DeliveryPortalException("The config file does not "
                                                      f"contain: '{c}'.")
                return credentials
        else:   # If config file is not entered check other options
            if username is None or password is None:
                raise DeliveryPortalException("Delivery Portal login credentials "
                                              "not specified. Enter --username/-u "
                                              "AND --password/-pw, or --config/-c."
                                              "For help: 'dp_api --help'.")
            else:
                if project is None:
                    raise DeliveryPortalException("Project not specified. Enter "
                                                  "project ID using --project option "
                                                  "or add to config file using --config/-c"
                                                  "option.")
                return {'username': username,
                        'password': password,
                        'project': project,
                        'owner': owner}


def check_access(login_info: dict) -> (str):
    """Checks the users access to the delivery portal and the specified project,
    and the projects S3 access.

    Args:
        login_info:     Dictionary containing username, password and project ID.

    Returns:
        str:    User ID connected to the specified user.

    """

    # Get user specified options
    username = login_info['username']
    password = login_info['password']
    project = login_info['project']
    owner = login_info['owner']

    try:
        user_db = couch_connect()['user_db']    # Connect to user database
    except CouchDBException as cdbe:
        sys.exit(f"Could not collect database 'user_db'. {cdbe}")
    else:
        for id_ in user_db:  # Search the database for the user
            if username == user_db[id_]['username']:  # If found check password
                if (user_db[id_]['password']['hash'] !=
                        secure_password_hash(password_settings=user_db[id_]['password']['settings'],
                                             password_entered=password)):
                    raise DeliveryPortalException("Wrong password. "
                                                  "Access to Delivery Portal denied.")
                else:   # Correct password
                    calling_command = sys._getframe().f_back.f_code.co_name  # get or put

                    # If facility is uploading or researcher is downloading, access is granted
                    if (user_db[id_]['role'] == 'facility' and calling_command == "put" and owner is not None) or \
                            (user_db[id_]['role'] == 'researcher' and calling_command == "get" and owner is None):
                        # Check project access
                        project_access_granted = project_access(user=id_,
                                                                project=project,
                                                                owner=owner)
                        if not project_access_granted:
                            raise DeliveryPortalException(
                                "Project access denied. Cancelling upload."
                            )
                        else:
                            if 's3_project' not in user_db[id_]:
                                raise DeliveryPortalException("Safespring S3 project not specified. "
                                                              "Cannot proceed with delivery. Aborted.")
                            else:
                                try:
                                    s3_project = user_db[id_]['s3_project']['name']
                                except DeliveryPortalException as dpe:
                                    sys.exit("Could not get Safespring S3 project name from database."
                                             f"{dpe}.\nDelivery aborted. ")
                                else:
                                    return id_, s3_project

                    else:  # Otherwise there is an option error.
                        if owner is None:
                            raise DeliveryOptionException("You did not specify the data owner."
                                                          "For help: 'dp_api --help'")
                        else:
                            raise DeliveryOptionException("Chosen upload/download "
                                                          "option not granted. "
                                                          f"You chose: '{calling_command}'. "
                                                          "For help: 'dp_api --help'")
        # The user not found.
        raise CouchDBException("Username not found in database. "
                               "Access to Delivery Portal denied.")


def project_access(user: str, project: str, owner: str) -> (bool):
    """Checks the users access to a specific project.

    Args:
        user:       User ID.
        project:    ID of project that the user is requiring access to.
        owner:      Owner of project.

    Returns:
        bool:   True if project access granted

    """

    try:
        couch = couch_connect()    # Connect to database
    except CouchDBException as cdbe:
        sys.exit(f"Could not connect to CouchDB: {cdbe}")
    else:
        # Get the projects registered for the user
        user_projects = couch['user_db'][user]['projects']

        # If the specified project does not exist in the project database quit
        if project not in couch['project_db']:
            raise CouchDBException(f"The project {project} does not exist.")
        else:
            # If the specified project does not exist in the users project list quit
            if project not in user_projects:
                raise DeliveryOptionException("You do not have access to the specified project "
                                              f"{project}. Aborting upload.")
            else:
                project_db = couch['project_db'][project]
                # If the project exists but does not have any 'project_info'
                # raise exception and quit
                if 'project_info' not in project_db:
                    raise CouchDBException("There is no 'project_info' recorded "
                                           "for the specified project.")
                else:
                    # If the specified project does not have a owner quit
                    if 'owner' not in project_db['project_info']:
                        raise CouchDBException("A owner of the data has not been "
                                               "specified. Cannot guarantee data "
                                               "security. Cancelling delivery.")
                    else:
                        # The user is a facility and has specified a data owner
                        # or the user is the owner and is a researcher
                        if (owner is not None and owner == project_db['project_info']['owner']) or \
                                (owner is None and user == project_db['project_info']['owner']):
                            # If the project delivery option is not S3, raise except and quit
                            if 'delivery_option' not in project_db['project_info']:
                                raise CouchDBException("A delivery option has not been "
                                                       "specified for this project. ")
                            else:
                                if not project_db['project_info']['delivery_option'] == "S3":
                                    raise DeliveryOptionException("The specified project does "
                                                                  "not have access to S3 delivery.")
                                else:
                                    return True  # No exceptions - access granted
                        else:
                            raise DeliveryOptionException("Incorrect data owner! You do not "
                                                          "have access to this project. "
                                                          "Cancelling delivery.")


# Path processing # # # # # # # # # # # # # # # # # # # # # # Path processing #

def create_directories(tdir: str) -> (bool, tuple):
    """Creates all temporary directories.

    Args:
        tdir:   Path to new temporary directory
        paths:  Tuple containing all data-file paths

    Returns:
        tuple:  Tuple containing

            bool:   True if directories created
            tuple:  All created directories
    """

    dirs = tuple(p for p in [tdir,
                             f"{tdir}/files",
                             f"{tdir}/keys",
                             f"{tdir}/meta",
                             f"{tdir}/logs"])

    for d_ in dirs:
        try:
            os.mkdir(d_)
        except OSError as ose:
            click.echo(f"The directory '{d_}' could not be created: {ose}"
                       "Cancelling delivery. Deleting temporary directory.")
            return False

    return True, dirs


def s3_upload(file: str, spec_path: str, sub_path: str, s3_resource, bucket) -> (str):
    """Handles processing of files including compression and encryption.

    Args:
        file:           File to be uploaded
        spec_path:      The original specified path 
        sub_path:       The current subfolder 
        s3_resource:    The S3 connection resource
        bucket:         S3 bucket to upload to

    """

    filetoupload = os.path.abspath(file)
    filename = os.path.basename(filetoupload)

    root_folder = os.path.basename(os.path.normpath(spec_path))
    all_subfolders = filetoupload.split(root_folder)

    # print(f"subfolders : {all_subfolders} \t length: {len(all_subfolders)} \n last is filename? : {all_subfolders[-1]}, {filename}\n" )
    if len(all_subfolders) == 2 and all_subfolders[-1] == f"/{filename}":
        response = s3_resource.meta.client.list_objects_v2(
            Bucket=bucket.name,
            Prefix="",
        )
        for obj in response.get('Contents', []):
            print("---->", obj)
            if obj['Key'] == root_folder:
                print(f"the folder {root_folder} exists")
            else:
                s3_resource.meta.client.put_object(Bucket=bucket.name,
                                                   Key=f"{root_folder}/")
    else:
        all_subfolders = all_subfolders[-1].split("/")
        # for each folder check if exists and then put file in there
        path_from_root = "files"
        for folder in all_subfolders[1:-1]:
            print("subfolder: ", folder)

    # Upload file
    MB = 1024 ** 2
    GB = 1024 ** 3
    config = TransferConfig(multipart_threshold=5*GB, multipart_chunksize=5*MB)
    if bucket in s3_resource.buckets.all():
        print(len(all_subfolders))
        if len(all_subfolders) > 2:
            print("här")
            for folder in all_subfolders:
                print("folder: ", folder)

        if file_exists_in_bucket(s3_resource=s3_resource, bucketname=bucket.name, key=filename):
            return f"File exists: {filename}, not uploading file."
        else:
            try:
                s3_resource.meta.client.upload_file(filetoupload, bucket.name,
                                                    f"{root_folder}/{filename}", Config=config)
            except Exception as e:
                print("Something wrong: ", e)
            else:
                return f"Success: {filetoupload} uploaded to S3!"


# S3 specific # # # # # # # # # # # # # # # # # # # # # # # # # # # # S3 specific #


def get_s3_info(current_project: str, s3_proj: str):
    """Gets the users s3 credentials including endpoint and key pair,
    and a bucket object representing the current project.

    Args:
        current_project:    The project ID to which the data belongs.
        s3_proj:            Safespring S3 project, facility specific.

    Returns:
        tuple:  Tuple containing

            s3_resource:    S3 resource (connection)
            bucket:         S3 bucket to upload to/download from

        """

    # Project access granted -- Get S3 credentials
    s3path = str(Path(os.getcwd())) + "/sensitive/s3_config.json"
    with open(s3path) as f:
        s3creds = json.load(f)

    # Keys and endpoint from file - this will be changed to database
    endpoint_url = s3creds['endpoint_url']
    project_keys = s3creds['sfsp_keys'][s3_proj]

    # Start s3 connection resource
    s3_resource = boto3.resource(
        service_name='s3',
        endpoint_url=endpoint_url,
        aws_access_key_id=project_keys['access_key'],
        aws_secret_access_key=project_keys['secret_key'],
    )

    # Bucket to upload to specified by user
    bucketname = f"project_{current_project}"
    bucket = s3_resource.Bucket(bucketname)

    return s3_resource, bucket


def file_exists_in_bucket(s3_resource, bucketname, key: str) -> (bool):
    """Checks if the current file already exists in the specified bucket.
    If so, the file will not be uploaded.

    Args:
        s3_resource:    Boto3 S3 resource
        bucket:         Name of bucket to check for file
        key:            Name of file to look for

    Returns:
        bool:   True if the file already exists, False if it doesnt

    """

    response = s3_resource.meta.client.list_objects_v2(
        Bucket=bucketname,
        Prefix=key,
    )
    for obj in response.get('Contents', []):
        if obj['Key'] == key:
            return True

    return False


# Testing # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # Testing #

def testfunction(file):
    return f"{time.time()} \t {file}"


# MAIN ################################################################## MAIN #

@click.group()
def cli():
    global COMPRESSED_FORMATS
    COMPRESSED_FORMATS = compression_dict()


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
              required=False,
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

    all_files = list()      # List of all files to be uploaded
    upload_path = dict()    # format: {original-file:file-to-be-uploaded}
    hash_dict = dict()      # format: {original-file:hmac}
    failed = dict()         # failed file/folder uploads

    # Check for all required login credentials and project and return in correct format
    user_info = verify_user_input(config=config,
                                  username=username,
                                  password=password,
                                  project=project,
                                  owner=owner)

    # Check user access to DP and project, and project to S3 delivery option
    user_id, s3_proj = check_access(login_info=user_info)

    if not isinstance(user_id, str):
        raise DeliveryPortalException("User ID not set, "
                                      "cannot proceed with data delivery.")

    # If no files are entered --> quit
    if not data and not pathfile:
        raise DeliveryPortalException(
            "No data to be uploaded. Specify individual files/folders using "
            "the --data/-d option one or more times, or the --pathfile/-f. "
            "For help: 'dp_api --help'"
        )
    else:
        # If --data option --> put all files in list
        if data is not None:
            all_files = [os.path.abspath(d) if os.path.exists(d)
                         else [None, d] for d in data]

        # If --pathfile option --> put all files in list
        if pathfile is not None:
            pathfile_abs = os.path.abspath(pathfile)
            # Precaution, already checked in click.option
            if os.path.exists(pathfile_abs):
                with open(pathfile_abs, 'r') as file:  # Read lines, strip \n and put in list
                    all_files += [os.path.abspath(line.strip()) if os.path.exists(line.strip())
                                  else [None, line.strip()] for line in file]
            else:
                raise IOError(
                    f"--pathfile option {pathfile} does not exist. Cancelling delivery.")

            # Check for file duplicates
            for element in all_files:
                if all_files.count(element) != 1:
                    raise DeliveryOptionException(f"The path to file {element} is listed multiple times, "
                                                  "please remove path dublicates.")

        # This should never be able to be true - just precaution
        if not all_files:
            raise DeliveryPortalException("Data tuple empty. Nothing to upload."
                                          "Cancelling delivery.")

    # Create temporary folder with timestamp and all subfolders
    timestamp = get_current_time().replace(" ", "_").replace(":", "-")
    temp_dir = f"{os.getcwd()}/DataDelivery_{timestamp}"
    dirs_created, dirs = create_directories(tdir=temp_dir)
    if not dirs_created:  # If error when creating one of the folders
        if os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)  # Remove all prev created folders
                sys.exit(f"Temporary directory deleted. \n\n"
                         "----DELIVERY CANCELLED---\n")  # and quit
            except OSError as ose:
                sys.exit(f"Could not delete directory {temp_dir}: {ose}\n\n "
                         "----DELIVERY CANCELLED---\n")
    else:
        logging.basicConfig(filename=f"{temp_dir}/logs/data-delivery.log",
                            level=logging.DEBUG)

    s3_resource, project_bucket = get_s3_info(current_project=user_info['project'],
                                              s3_proj=s3_proj)

    # Create multithreading pool
    with concurrent.futures.ThreadPoolExecutor() as executor:
        upload_threads = []
        print(f"All files: {all_files}")
        for path in all_files:
            if type(path) == str:
                # check if folder and then get all subfolders
                if os.path.isdir(path):
                    print(f"Path: {path}")
                    all_dirs = [x[0] for x in os.walk(path)]  # all (sub)dirs
                    print(f"All directories: {all_dirs}")
                    for dir_ in all_dirs:
                        # check which files are in the directory
                        all_files = [os.path.join(dir_, f) for f in os.listdir(dir_)
                                     if os.path.isfile(os.path.join(dir_, f))]
                        print(f"Current directory: {dir_}")
                        print(f"All files: {all_files}")
                        # Upload all files
                        for file in all_files:
                            print(f"File: {file} \n"
                                  f"Path: {path} \n "
                                  f"Directory: {dir_} \n")
                            future = executor.submit(s3_upload, file, path, dir_,
                                                     s3_resource, project_bucket)
                            upload_threads.append(future)
                elif os.path.isfile(path):
                    print(path)
                    # Upload file
                    future = executor.submit(s3_upload, path,
                                             s3_resource, project_bucket)
                    upload_threads.append(future)
                else:
                    sys.exit(f"Path type {path} not identified."
                             "Have you entered the correct path?")

        for f in concurrent.futures.as_completed(upload_threads):
            print(f.result())


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
              type=click.Path(exists=True),
              help="Path to file or folder to upload.")
def get(config: str, username: str, password: str, project: str,
        pathfile: str, data: tuple):
    """Downloads the files from S3 bucket. Not usable by facilities. """

    click.echo("download function")
