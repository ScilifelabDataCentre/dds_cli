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

class DPUser():
    ''''''

    def __init__(self, username=None, password=None):
        ''''''

        self.username = username
        self.password = password
        self.id = None
        self.role = None


class S3Object():
    ''''''

    def __init__(self):
        ''''''

        self.resource = None
        self.project = None
        self.bucket = None

    def get_info(self, current_project: str):
        '''Gets the users s3 credentials including endpoint and key pair,
        and a bucket object representing the current project.

        Args:
            current_project:    The project ID to which the data belongs.
            s3_proj:            Safespring S3 project, facility specific.

        Returns:
            tuple:  Tuple containing

                s3_resource:    S3 resource (connection)
                bucket:         S3 bucket to upload to/download from

        '''

        # Project access granted -- Get S3 credentials
        s3path = str(Path(os.getcwd())) + "/sensitive/s3_config.json"
        with open(s3path) as f:
            s3creds = json.load(f)

        # Keys and endpoint from file - this will be changed to database
        endpoint_url = s3creds['endpoint_url']
        project_keys = s3creds['sfsp_keys'][self.project]

        # Start s3 connection resource
        self.resource = boto3.resource(
            service_name='s3',
            endpoint_url=endpoint_url,
            aws_access_key_id=project_keys['access_key'],
            aws_secret_access_key=project_keys['secret_key'],
        )

        # Bucket to upload to specified by user
        bucketname = f"project_{current_project}"
        self.bucket = self.resource.Bucket(bucketname)


class DataDeliverer():
    '''
    Raises:
        DeliveryPortalException:    All required info not found
        OSError:                    Config file not found
    '''

    def __init__(self, config=None, username=None, password=None,
                 project_id=None, project_owner=None, pathfile=None, data=None):

        # If none of username, password and config options are set
        # raise exception and quit execution -- dp cannot be accessed
        if all(x is None for x in [username, password, config]):
            raise DeliveryPortalException("Delivery Portal login credentials "
                                          "not specified. Enter: \n --username/-u "
                                          "AND --password/-pw, or --config/-c\n "
                                          "--owner/-o\n"
                                          "For help: 'dp_api --help'.")
        else:
            # put or get
            self.method = sys._getframe().f_back.f_code.co_name
            self.user = DPUser(username=username, password=password)
            self.project_id = project_id
            self.project_owner = project_owner
            self.data = None
            self.s3 = S3Object()

            self.check_user_input(config=config)

            dp_access_granted, self.user.id = self.check_dp_access()
            if dp_access_granted and self.user.id is not None:
                proj_access_granted, self.s3.project = self.check_project_access()
                if proj_access_granted and self.s3.project is not None:
                    # If no data to upload, cancel
                    if not data and not pathfile:
                        raise DeliveryPortalException(
                            "No data to be uploaded. Specify individual files/folders using "
                            "the --data/-d option one or more times, or the --pathfile/-f. "
                            "For help: 'dp_api --help'"
                        )
                    else:
                        self.data = self.data_to_deliver(data=data,
                                                         pathfile=pathfile)
                else:
                    raise DeliveryPortalException(f"Access to project {self.project_id} "
                                                  "denied. Delivery cancelled.")
            else:
                raise DeliveryPortalException("Delivery Portal access denied! "
                                              "Delivery cancelled.")

            if self.data is not None:
                dirs_created, self.tempdir = self.create_directories()
                if not dirs_created:
                    raise DeliveryPortalException(
                        "Temporary directory could not be created. Unable to continue delivery. Aborting. ")

                self.s3.get_info(self.project_id)

    def check_user_input(self, config):
        ''''''
        if config is not None:              # If config file entered
            if os.path.exists(config):      # and exist
                try:
                    with open(config, 'r') as cf:
                        credentials = json.load(cf)
                except OSError as ose:
                    sys.exit(f"Could not open path-file {config}: {ose}")

                # Check that all credentials are entered and quit if not
                for c in ['username', 'password', 'project', 'owner']:
                    if c not in credentials:
                        raise DeliveryPortalException("The config file does not "
                                                      f"contain: '{c}'.")

                self.user.username = credentials['username']
                self.user.password = credentials['password']
                self.project_id = credentials['project']
                self.project_owner = credentials['owner']

        else:
            if self.user.username is None or self.user.password is None:
                raise DeliveryPortalException("Delivery Portal login credentials "
                                              "not specified. Enter --username/-u "
                                              "AND --password/-pw, or --config/-c."
                                              "For help: 'dp_api --help'.")
            else:
                if self.project_id is None:
                    raise DeliveryPortalException("Project not specified. Enter "
                                                  "project ID using --project option "
                                                  "or add to config file using --config/-c"
                                                  "option.")

                # If no owner is set then assuming current user is owner
                if self.project_owner is None:
                    self.project_owner = self.user.username

    def check_dp_access(self):
        ''''''
        try:
            user_db = couch_connect()['user_db']
        except CouchDBException as cdbe:
            sys.exit(f"Could not collect database 'user_db'. {cdbe}")
        else:
            # Search the database for the user
            for id_ in user_db:
                # If found, create secure password hash and compare to correct password
                if self.user.username == user_db[id_]['username']:
                    password_settings = user_db[id_]['password']['settings']
                    password_hash = secure_password_hash(password_settings=password_settings,
                                                         password_entered=self.user.password)
                    if user_db[id_]['password']['hash'] != password_hash:
                        raise DeliveryPortalException("Wrong password. "
                                                      "Access to Delivery Portal denied.")
                    else:
                        # Check that facility is uploading or researcher downloading
                        self.user.role = user_db[id_]['role']
                        if (self.user.role == 'facility' and self.method == 'put') or \
                                (self.user.role == 'researcher' and self.method == 'get'):
                            return True, id_

            # The user not found.
            raise CouchDBException("Username not found in database. "
                                   "Access to Delivery Portal denied.")

    def check_project_access(self):
        ''''''
        try:
            couch = couch_connect()  # Connect to database
        except CouchDBException as cdbe:
            sys.exit(f"Could not connect to CouchDB: {cdbe}")
        else:
            user_db = couch['user_db']
            # Get the projects registered to the user
            user_projects = user_db[self.user.id]['projects']
            # Check if project exists in project database
            if self.project_id not in couch['project_db']:
                raise CouchDBException(
                    f"The project {self.project_id} does not exist.")
            else:
                # If user does not have access to the project, quit
                if self.project_id not in user_projects:
                    raise DeliveryOptionException("You do not have access to the specified project "
                                                  f"{self.project_id}. Aborting delivery.")
                else:
                    current_project = couch['project_db'][self.project_id]
                    # Get project information if it exists
                    if 'project_info' not in current_project:
                        raise CouchDBException("There is no 'project_info' recorded "
                                               "for the specified project. Aborting delivery.")
                    else:
                        # Find owner of project and check if specified owner matches
                        if 'owner' not in current_project['project_info']:
                            raise CouchDBException("An owner of the data has not been "
                                                   "specified. Cannot guarantee data "
                                                   "security. Cancelling delivery.")
                        else:
                            correct_owner = current_project['project_info']['owner']
                            # If facility specified correct user or researcher is owner
                            if (self.method == 'put' and correct_owner == self.project_owner != self.user.id) or \
                                    (self.method == 'get' and correct_owner == self.project_owner == self.user.id):
                                if 'delivery_option' not in current_project['project_info']:
                                    raise CouchDBException("A delivery option has not been "
                                                           "specified for this project.")
                                else:
                                    if current_project['project_info']['delivery_option'] != "S3":
                                        raise DeliveryOptionException("The specified project does not "
                                                                      "have access to S3 delivery.")
                                    else:
                                        try:
                                            s3_project = user_db[self.user.id]['s3_project']['name']
                                        except DeliveryPortalException as dpe:
                                            sys.exit("Could not get Safespring S3 project name from database."
                                                     f"{dpe}. \nDelivery aborted.")
                                        else:
                                            return True, s3_project
                            else:
                                raise DeliveryOptionException("Incorrect data owner! You do not "
                                                              "have access to this project. "
                                                              "Cancelling delivery.")

    def data_to_deliver(self, data: tuple, pathfile: str) -> (list):
        ''''''

        all_files = list()

        # If --data option --> put all files in list
        if data is not None:
            if self.method == "put":
                all_files = [os.path.abspath(d) if os.path.exists(d)
                             else [None, d] for d in data]
            elif self.method == "get":
                all_files = [d for d in data]
            else:
                pass    # raise an error here

        # If --pathfile option --> put all files in list
        if pathfile is not None:
            pathfile_abs = os.path.abspath(pathfile)
            # Precaution, already checked in click.option
            if os.path.exists(pathfile_abs):
                with open(pathfile_abs, 'r') as file:  # Read lines, strip \n and put in list
                    if self.method == "put":
                        all_files += [os.path.abspath(line.strip()) if os.path.exists(line.strip())
                                      else [None, line.strip()] for line in file]
                    elif self.method == "get":
                        all_files += [line.strip() for line in file]
                    else:
                        pass    # raise an error here
            else:
                raise IOError(
                    f"--pathfile option {pathfile} does not exist. Cancelling delivery.")

        # Check for file duplicates
        for element in all_files:
            if all_files.count(element) != 1:
                raise DeliveryOptionException(f"The path to file {element} is listed multiple times, "
                                              "please remove path dublicates.")

        return all_files

    def create_directories(self):
        ''''''
        # Create temporary folder with timestamp and all subfolders
        timestamp_ = timestamp()
        temp_dir = f"{os.getcwd()}/DataDelivery_{timestamp_}"
        dirs = tuple(
            f"{temp_dir}/{sf}" for sf in ["", "files/", "keys/", "meta/", "logs/"])

        for d_ in dirs:
            try:
                os.mkdir(d_)
            except OSError as ose:
                click.echo(f"The directory '{d_}' could not be created: {ose}"
                           "Cancelling delivery. Deleting temporary directory.")

                if os.path.exists(temp_dir):
                    try:
                        # Remove all prev created folders
                        shutil.rmtree(temp_dir)
                        sys.exit(f"Temporary directory deleted. \n\n"
                                 "----DELIVERY CANCELLED---\n")  # and quit
                    except OSError as ose:
                        sys.exit(f"Could not delete directory {temp_dir}: {ose}\n\n "
                                 "----DELIVERY CANCELLED---\n")

                        return False, ()

                else:
                    pass  # create log file here
                    # logging.basicConfig(filename=f"{temp_dir}/logs/data-delivery.log",
                    #         level=logging.DEBUG)

        return True, dirs

    def put(self):
        ''''''

        # Create multithreading pool
        with concurrent.futures.ThreadPoolExecutor() as executor:
            upload_threads = []
            for path in self.data:
                if type(path) == str:
                    # check if folder and then get all subfolders
                    if os.path.isdir(path):
                        all_dirs = [x[0]
                                    for x in os.walk(path)]  # all (sub)dirs
                        for dir_ in all_dirs:
                            # check which files are in the directory
                            all_files = [os.path.join(dir_, f) for f in os.listdir(dir_)
                                         if os.path.isfile(os.path.join(dir_, f))]
                            # Upload all files
                            for file in all_files:
                                future = executor.submit(s3_upload, file, path,
                                                         self.s3.resource, self.s3.bucket)
                                upload_threads.append(future)
                    elif os.path.isfile(path):
                        # Upload file
                        future = executor.submit(s3_upload, path, None,
                                                 self.s3.resource, self.s3.bucket)
                        upload_threads.append(future)
                    else:
                        sys.exit(f"Path type {path} not identified."
                                 "Have you entered the correct path?")

            for f in concurrent.futures.as_completed(upload_threads):
                print(f.result())

    def get(self):
        ''''''

        pass

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


def timestamp() -> (str):
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

    return timestamp.replace(" ", "_").replace(":", "-")


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
        owner:      The owner of the data/project, "" if downloading 

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

def collect_all_data(data: tuple, pathfile: str) -> (list):
    """Puts all entered paths into one list

    Args: 
        data:       Tuple containing paths
        pathfile:   Path to file containing paths

    Returns: 
        list: List of all paths entered in data and pathfile option

    """

    all_files = list()

    delivery_option = sys._getframe().f_back.f_code.co_name

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
            if delivery_option == "put":
                all_files = [os.path.abspath(d) if os.path.exists(d)
                             else [None, d] for d in data]
            elif delivery_option == "get":
                all_files = [d for d in data]
            else:
                pass    # raise an error here

        # If --pathfile option --> put all files in list
        if pathfile is not None:
            pathfile_abs = os.path.abspath(pathfile)
            # Precaution, already checked in click.option
            if os.path.exists(pathfile_abs):
                with open(pathfile_abs, 'r') as file:  # Read lines, strip \n and put in list
                    if delivery_option == "put":
                        all_files += [os.path.abspath(line.strip()) if os.path.exists(line.strip())
                                      else [None, line.strip()] for line in file]
                    elif delivery_option == "get":
                        all_files += [line.strip() for line in file]
                    else:
                        pass    # raise an error here
            else:
                raise IOError(
                    f"--pathfile option {pathfile} does not exist. Cancelling delivery.")

            # Check for file duplicates
            for element in all_files:
                if all_files.count(element) != 1:
                    raise DeliveryOptionException(f"The path to file {element} is listed multiple times, "
                                                  "please remove path dublicates.")
    return all_files


def create_directories(dirs: str, temp_dir: str) -> (bool, tuple):
    """Creates all temporary directories.

    Args:
        tdir:   Path to new temporary directory

    Returns:
        tuple:  Tuple containing

            bool:   True if directories created
            tuple:  All created directories
    """

    print("Directories: ", dirs)
    for d_ in dirs:
        try:
            os.mkdir(d_)
        except OSError as ose:
            click.echo(f"The directory '{d_}' could not be created: {ose}"
                       "Cancelling delivery. Deleting temporary directory.")

            if os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)  # Remove all prev created folders
                    sys.exit(f"Temporary directory deleted. \n\n"
                             "----DELIVERY CANCELLED---\n")  # and quit
                except OSError as ose:
                    sys.exit(f"Could not delete directory {temp_dir}: {ose}\n\n "
                             "----DELIVERY CANCELLED---\n")

            return False

        else:
            pass  # create log file here
            # logging.basicConfig(filename=f"{temp_dir}/logs/data-delivery.log",
            #         level=logging.DEBUG)

    return True


def s3_upload(file: str, spec_path: str, s3_resource, bucket) -> (str):
    """Handles processing of files including compression and encryption.

    Args:
        file:           File to be uploaded
        spec_path:      The original specified path, None if single specified file
        s3_resource:    The S3 connection resource
        bucket:         S3 bucket to upload to

    """

    filetoupload = os.path.abspath(file)
    filename = os.path.basename(filetoupload)

    root_folder = ""
    filepath = ""
    all_subfolders = ""

    # Upload file
    MB = 1024 ** 2
    GB = 1024 ** 3
    config = TransferConfig(multipart_threshold=5*GB, multipart_chunksize=5*MB)

    # check if bucket exists
    if bucket in s3_resource.buckets.all():
        # if file, not within folder
        if spec_path is None:
            filepath = filename
        else:
            root_folder = os.path.basename(os.path.normpath(spec_path))
            filepath = f"{root_folder}{filetoupload.split(root_folder)[-1]}"
            all_subfolders = f"{filepath.split(filename)[0]}"

            # check if folder exists
            response = s3_resource.meta.client.list_objects_v2(
                Bucket=bucket.name,
                Prefix="",
            )

            found = False
            for obj in response.get('Contents', []):
                if obj['Key'] == all_subfolders:
                    found = True
                    break

            if not found:   # if folder doesn't exist then create folder
                s3_resource.meta.client.put_object(Bucket=bucket.name,
                                                   Key=all_subfolders)

        # check if file exists
        if file_exists_in_bucket(s3_resource=s3_resource, bucketname=bucket.name, key=filepath):
            return f"File exists: {filename}, not uploading file."
        else:
            try:
                s3_resource.meta.client.upload_file(filetoupload, bucket.name,
                                                    filepath, Config=config)
            except Exception as e:
                print("Something wrong: ", e)
            else:
                return f"Success: {filetoupload} uploaded to S3!"


def s3_download(file: str, s3_resource, bucket, dl_file: str) -> (str):
    """Downloads the specified files

    Args: 
        file:           File to be downloaded
        s3_resource:    S3 connection
        bucket:         Bucket to download from
        dl_file:        Name of downloaded file

    Returns:
        str:    Success message if download successful 

    """
    print(file, os.path.basename(file))
    # check if bucket exists
    if bucket in s3_resource.buckets.all():

        # check if file exists
        if not file_exists_in_bucket(s3_resource=s3_resource, bucketname=bucket.name, key=file) and not \
                file_exists_in_bucket(s3_resource=s3_resource, bucketname=bucket.name, key=f"{file}/"):
            return f"File does not exist: {file}, not downloading anything."
        else:
            try:
                s3_resource.meta.client.download_file(
                    bucket.name, file, dl_file)
            except Exception as e:
                print("Something wrong: ", e)
            else:
                return f"Success: {file} downloaded from S3!"


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

        print(f"{delivery.method}, {delivery.project_id}, {delivery.project_owner}, "
              f"\n{delivery.user.username}, {delivery.user.password}, {delivery.user.id}")
        print(f"{delivery.tempdir},\n {delivery.s3.resource}, {delivery.s3.project}, {delivery.s3.bucket}, {delivery.s3.bucket.name}")

        delivery.put()


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

    all_files = list()

    user_info = verify_user_input(config=config,
                                  username=username,
                                  password=password,
                                  project=project)

    user_id, s3_proj = check_access(login_info=user_info)

    if not isinstance(user_id, str):
        raise DeliveryPortalException("User ID not set, "
                                      "cannot proceed with data delivery.")

    all_files = collect_all_data(data=data, pathfile=pathfile)

    # This should never be able to be true - just precaution
    if not all_files:
        raise DeliveryPortalException("Data tuple empty. Nothing to upload."
                                      "Cancelling delivery.")

    # Create temporary folder with timestamp and all subfolders
    timestamp = get_current_time().replace(" ", "_").replace(":", "-")
    temp_dir = f"{os.getcwd()}/DataDelivery_{timestamp}"
    dirs = tuple(
        f"{temp_dir}/{sf}" for sf in ["", "files/", "keys/", "meta/", "logs/"])

    dirs_created = create_directories(dirs=dirs, temp_dir=temp_dir)
    if not dirs_created:  # If error when creating one of the folders
        pass    # raise exception here

    s3_resource, project_bucket = get_s3_info(current_project=user_info['project'],
                                              s3_proj=s3_proj)

    # Create multithreading pool
    with concurrent.futures.ThreadPoolExecutor() as executor:
        upload_threads = []
        for path in all_files:
            if type(path) == str:
                # Download all files
                future = executor.submit(s3_download, path,
                                         s3_resource, project_bucket, f"{temp_dir}/files/{path}")
                upload_threads.append(future)

        for f in concurrent.futures.as_completed(upload_threads):
            print(f.result())
