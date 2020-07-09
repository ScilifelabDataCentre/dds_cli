# IMPORTS

from cryptography.hazmat.primitives import hashes, hmac
from cryptography.hazmat.primitives.kdf.scrypt imporat Scrypt
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
import shutil
import zipfile
import zlib
import tarfile
import gzip
import json
import tempfile
import couchdb
import hashlib
import os
import filetype
import mimetypes
from typing import Union
import datetime
from itertools import chain
from ctypes import *
from crypt4gh import lib, header, keys
from functools import partial
from getpass import getpass

from code_api.dp_exceptions import *
from botocore.exceptions import ClientError

import boto3
from boto3.s3.transfer import TransferConfig
import smart_open

import time
import traceback

from code_api.datadel_s3 import S3Object
from code_api.data_deliverer import DataDeliverer, DPUser

from tqdm_multi_thread import TqdmMultiThreadFactory

# .-------------


# CHECK CALLING FUNCTION
cur_com = sys._getframe().f_code.co_name  # The current command, "put" here
# The calling function ("invoke" in this case)
cal_com = sys._getframe().f_back.f_code.co_name


# ENCRYPTION KEY CLASS
class ECDHKeyPair:
    """Public key pair.
    Algorithm: Eliptic Curve Diffie-Hellman (Curve25519)"""

    def __init__(self, privatekey: str = "key", publickey: str = "key", temp_dir: str = ""):
        """Generates a public key pair"""

        cb = partial(get_passphrase)    # Get passphrase for private key enc

        # Directory for storing keys
        key_dir = f"{temp_dir}/keys"

        # Paths to private and public keys
        priv_keyname = f"{key_dir}/{privatekey}.sec"
        pub_keyname = f"{key_dir}/{publickey}.pub"

        try:
            # Generate public key pair, encrypt private key
            keys.c4gh.generate(seckey=priv_keyname,
                               pubkey=pub_keyname, callback=cb)
        except EncryptionError as ee:
            self.pub = f"The key pair {priv_keyname}/{pub_keyname} could not be generated: {ee}"
            self.sec = None
        else:
            try:
                # Import keys, decrypt private key
                self.pub = keys.get_public_key(filepath=pub_keyname)
                self.sec = keys.get_private_key(filepath=priv_keyname,
                                                callback=cb)
            except EncryptionError as ee:
                sys.exit(
                    f"Could not get the keys {priv_keyname} & {pub_keyname}: ", f"{ee}")

    def encrypt(self, file: str, remote_pubkey, temp_dir: str, sub_dir: str):
        """Uses the remote public key and the own private key to encrypt a file"""

        error = ""

        fname = file.split('/')[-1]
        if sub_dir == "":
            encrypted_file = f"{temp_dir}/{fname}.c4gh"
        else:
            encrypted_file = f"{sub_dir}/{fname}.c4gh"

        try:
            # Encrypt file
            with open(file=file, mode='rb') as infile:
                with open(file=encrypted_file, mode='wb+') as outfile:
                    # The 0 in keys is the method (only one allowed)
                    lib.encrypt(keys=[(0, self.sec, remote_pubkey)],
                                infile=infile, outfile=outfile)
        except EncryptionError as ee:
            logging.error("Some error message here.")
            error = f"Could not encrypt file {file}: {ee}"
        else:
            logging.info("Some success message here.")

        return encrypted_file, "crypt4gh", error


# CREATE HEADER FOR CRYPT4GH FORMAT BEFORE CHUNK ENCRYPTION
def generate_header(own_private_key, remote_public_key):
    """Generates crypt4gh format header"""

    encryption_method = 0           # ChaCha20
    session_key = os.urandom(32)    # Key (file)
    print(session_key)
    cipher = ChaCha20Poly1305(session_key)  # Cipher (file)

    # 'keys' format: (method, own-private-key, remote-public-key)
    keys = [(0, own_private_key, remote_public_key)]

    header_content = header.make_packet_data_enc(encryption_method=encryption_method,
                                                 session_key=session_key)
    header_packets = header.encrypt(packet=header_content,
                                    keys=keys)
    header_bytes = header.serialize(packets=header_packets)

    return header_bytes, cipher


# CHUNK ENCRYPTION
def _encrypt_segment(data, process, cipher):
    """Utility function to generate a nonce,
    encrypt data with Chacha20,
    and authenticate it with Poly1305."""

    try:
        nonce = os.urandom(12)
        encrypted_data = cipher.encrypt(nonce, data, None)  # No add
        # after producing the segment, so we don't start outputing when an error occurs
        process(nonce)
        process(encrypted_data)
        yield encrypted_data
    except EncryptionError as ee:
        yield "error", f"Encryption of chunk failed: {ee}"


# CHUNK DECRYPTION
def try_decryption(encrypted_file: str, keypair: tuple):
    """Tests decryption of encrypted c4gh file"""

    # Deconstruct header
    # body decrypt
    with open(encrypted_file, 'rb') as ef:
        with open(f"{encrypted_file}.decrypted", 'wb') as df:
            lib.decrypt(keys=[(0, keypair[0], keypair[1])], infile=ef,
                        outfile=df, sender_pubkey=keypair[1], offset=0, span=65536)

    # NOT WORKING #
    hash_decrypted = hmac.HMAC(key=key, algorithm=hashes.SHA256(),
                               backend=default_backend())
    hash_decrypted = gen_hmac(filepath=f"{encrypted_file}.decrypted",
                              chunk_size=65536, hash_=hash_decrypted)

    return hash_decrypted


# CHUNK COMPRESSION
def compress_chunk(original_chunk):
    """Compress individual chunks read in a streamed fashion"""

    try:
        yield gzip.compress(data=original_chunk)
    except CompressionError as ce:
        yield "error", f"Compression of chunk failed: {ce}"


# CHUNK DECOMPRESSION
def decompress_chunk(compressed_chunk):
    """Performs gzip compression and streams compressed chunk"""

    yield gzip.decompress(compressed_chunk)


# COMPRESSION -- PROCESS_FILE
hash_original = ""                      # Original file hash
    hash_compressed = ""                    # Compressed file hash
    hash_encrypted = ""                     # Encrypted file hash

    key = b"Thisisakeythatshouldbechanged"
    h_orig = hmac.HMAC(key, hashes.SHA256(), backend=default_backend())
    h_comp = hmac.HMAC(key, hashes.SHA256(), backend=default_backend())

with open(file, 'rb') as f:
        print("Name: ", f.name)
        chunk_stream = stream_chunks(file_handle=f, chunk_size=65536)
        for chunk in chunk_stream:  # Continues here before above is finished
            if isinstance(chunk, tuple):
                logging.error("Some error message here.")
                return {"FAILED": {"Path": f.name,
                                   "Error": chunk[1]}}

            h_orig.update(chunk)    # Update hash for original file

            # If the file is not compressed, compress chunks
            if not is_compressed:
                comp_chunk_stream = compress_chunk(original_chunk=chunk)
                with open(file=f"{file}.gzip", mode='wb') as cf:
                    for comp_chunk in comp_chunk_stream:    # Continues here before above is finished
                        if isinstance(comp_chunk, tuple):
                            logging.error("Some error message here.")
                            return {"FAILED": {"Path": cf.name,
                                               "Error": comp_chunk[1]}}

                        # Updates hash for compressed file
                        h_comp.update(comp_chunk)

                        # Save compressed chunk to file
                        cf.write(comp_chunk)

                    is_compressed = True
                    compression_algorithm = "gzip"
                    latest_path = cf.name

            else:
                latest_path = file

    hash_original = h_orig.finalize().hex()
    hash_compressed = h_comp.finalize().hex()


# IF NOT SENSITIVE - NOT RELEVANT -- PROCESS_FILE
else:   # If not sensitive
	if is_compressed:   # If compressed
		# TODO: hash
		hash_compressed = gen_hmac(
			filepath=file, chunk_size=65536, hash_=hash_compressed)
	else:   # If NOT compressed
		# TODO: hash + compress + hash
		comp_dir = new_dir(filename=fname,
							sub_dir=sub_dir,
							temp_dir=temp_dir,
							operation="compression")
		hash_original, hash_compressed, \
			latest_path = hash_compress_hash_encrypt_hash(file=file,
															compressed_file=comp_dir,
															hash_original=hash_original,
															hash_compressed=hash_compressed)


# FILE PROCESSING -- ENCRYPTION ETC - PROCESS_FILE
if sensitive:
        # Generate keys
        researcher_kp = ECDHKeyPair(privatekey=f"{fname}_researcher",
                                    publickey=f"{fname}_researcher",
                                    temp_dir=temp_dir)
        facility_kp = ECDHKeyPair(privatekey=f"{fname}_facility",
                                  publickey=f"{fname}_facility",
                                  temp_dir=temp_dir)
        if researcher_kp.sec is None:
            logging.error("Some error message here.")
            return {"FAILED": {"Path": latest_path,
                               "Error": researcher_kp.pub}}
        elif facility_kp.sec is None:
            logging.error("Some error message here.")
            return {"FAILED": {"Path": latest_path,
                               "Error": facility_kp.pub}}

        if is_compressed:   # If file is compressed
            # TODO: hash + encrypt + hash
            enc_dir = new_dir(filename=fname,
                              sub_dir=sub_dir,
                              temp_dir=temp_dir,
                              operation="encryption")
            hash_compressed, hash_encrypted, \
                latest_path = hash_encrypt_hash(file=file,
                                                encrypted_file=enc_dir,
                                                keypair=(facility_kp.sec,
                                                         researcher_kp.pub),
                                                hash_compressed=hash_compressed,
                                                hash_encrypted=hash_encrypted)
        else:   # If file is NOT compressed
            # TODO: hash + compress + hash + encrypt + hash
            comp_dir = new_dir(filename=fname,
                               sub_dir=sub_dir,
                               temp_dir=temp_dir,
                               operation="compression")
            enc_dir = new_dir(filename=comp_dir.split("/")[-1],
                              sub_dir=sub_dir,
                              temp_dir=temp_dir,
                              operation="encryption")

            hash_original, hash_compressed, \
                hash_encrypted, latest_path = hash_compress_hash_encrypt_hash(file=file,
                                                                              encrypted_file=enc_dir,
                                                                              keypair=(facility_kp.sec,
                                                                                       researcher_kp.pub),
                                                                              hash_original=hash_original,
                                                                              hash_compressed=hash_compressed,
                                                                              hash_encrypted=hash_encrypted)

            hash_decrypted = try_decryption(
                encrypted_file=latest_path, keypair=(researcher_kp.sec, facility_kp.pub))
            print(hash_decrypted, hash_original,
                  hash_decrypted == hash_original)


# CHECKSUM GENERATION
def gen_hmac(filepath: str, chunk_size: int, hash_) -> str:
    """Generates HMAC for file"""

    try:
        with open(filepath, 'rb') as f:
            for compressed_chunk in iter(lambda: f.read(chunk_size), b''):
                hash_.update(compressed_chunk)
    except HashException as he:
        logging.error("Some error message here.")
        error = f"Checksum generation for file {filepath} failed. Can not guarantee file integrity. "
    else:
        logging.info("Some success message here.")

    return hash_.finalize().hex()

    # key = b"ina"
    # h = hmac.HMAC(key, hashes.SHA256(), backend=default_backend())

    # with open(filepath, 'rb') as f:
    #     for chunk in iter(lambda: f.read(16384), b''):
    #        h.update(chunk)

    # return h.finalize().hex(), error


# PROCESSING IN DIFFERENT ORDERS
def hash_compress_hash(file: str, compressed_file: str,
                       hash_original, hash_compressed) -> (str, str, str):
    """hash + compress + hash"""

    with open(file=file, mode='rb') as of:
        with open(file=compressed_file, mode='wb') as cf:
            chunk_stream = stream_chunks(file_handle=of, chunk_size=65536)
            for chunk in chunk_stream:
                hash_original.update(chunk)

                compressed_stream = compress_chunk(original_chunk=chunk)
                for compressed_chunk in compressed_stream:
                    hash_compressed.update(compressed_chunk)

                    cf.write(compressed_chunk)

    return hash_original.finalize().hex(), hash_compressed.finalize().hex(), \
        compressed_file


def hash_compress_hash_encrypt_hash(file: str, encrypted_file: str, keypair,
                                    hash_original, hash_compressed, hash_encrypted) -> (str, str, str, str):
    """hash + compress + hash + encrypt + hash"""

    header_bytes, cipher = generate_header(keypair[0], keypair[1])

    with open(file=file, mode='rb') as of:
        with open(file=encrypted_file, mode='wb') as ef:
            ef.write(header_bytes)
            chunk_stream = stream_chunks(file_handle=of, chunk_size=65536)
            for chunk in chunk_stream:
                hash_original.update(chunk)

                compressed_stream = compress_chunk(original_chunk=chunk)
                for compressed_chunk in compressed_stream:
                    hash_compressed.update(compressed_chunk)

                    encrypted_stream = _encrypt_segment(data=compressed_chunk,
                                                        process=ef.write,
                                                        cipher=cipher)
                    for encrypted_chunk in encrypted_stream:
                        hash_encrypted.update(encrypted_chunk)

    return hash_original.finalize().hex(), hash_compressed.finalize().hex(), \
        hash_encrypted.finalize().hex(), encrypted_file


def hash_encrypt_hash(file: str, encrypted_file: str, keypair,
                      hash_compressed, hash_encrypted) -> (str, str, str):
    """hash + encrypt + hash"""

    header_bytes, cipher = generate_header(keypair[0], keypair[1])

    with open(file=file, mode='rb') as cf:
        with open(file=encrypted_file, mode='wb') as ef:
            ef.write(header_bytes)
            chunk_stream = stream_chunks(file_handle=cf, chunk_size=65536)
            for compressed_chunk in chunk_stream:
                hash_compressed.update(compressed_chunk)
                encrypted_stream = _encrypt_segment(data=compressed_chunk,
                                                    process=ef.write,
                                                    cipher=cipher)
                for encrypted_chunk in encrypted_stream:
                    hash_encrypted.update(encrypted_chunk)

    return hash_compressed.finalize().hex(), \
        hash_encrypted.finalize().hex(), file


def hash_dir(dir_path: str, key) -> str:
    """Generates a hash for all contents within a folder"""

    # Initialize HMAC
    dir_hmac = hmac.HMAC(key, hashes.SHA256(), backend=default_backend())

    # Recursively walk through the folder
    for path, dirs, files in os.walk(dir_path):
        for file in sorted(files):  # For all files in folder root
            # Generate file hash and update directory hash
            dir_hmac.update(gen_hmac(os.path.join(path, file)))
        for dir_ in sorted(dirs):   # For all folders in folder root
            # Walk through child folder
            hash_dir(os.path.join(path, dir_), key)
        break

    return dir_hmac.finalize().hex()


# DATABASE STUFF -- COUCH DISCONNECTION
def couch_disconnect(couch, token):
    """Disconnect from couchdb interface."""

    try:
        couch.logout(token)
    except CouchDBException:
        print("Could not logout from database.")


# DELIVERY PORTAL ACCESS -- BASICALLY SAME THING AS IN CODE CHECK_ACCESS 
def dp_access(username: str, password: str, upload: bool) -> (bool, str):
    """Check existance of user in database and the password validity."""

    try:
        user_db = couch_connect()['user_db']    # Connect to user database
    except CouchDBException as cdbe:
        sys.exit(f"Could not collect database 'user_db'. {cdbe}")
    else:
        # Search the database for the user
        for id_ in user_db:
            # If the username does not exist in the database quit
            if username != user_db[id_]['username']:
                raise CouchDBException("Invalid username, "
                                       "user does not exist in database. ")
            else:
                # If the password isn't correct quit
                if user_db[id_]['password']['hash'] != secure_password_hash(password_correct=user_db[id_]['password'],
                                                                            password_entered=password):
                    raise DeliveryPortalException("Wrong password. "
                                                  "Access to Delivery Portal "
                                                  "denied.")
                else:
                    # If facility is uploading or researcher is downloading
                    # access is granted
                    if (user_db[id_]['role'] == 'facility' and upload) or \
                            (user_db[id_]['role'] == 'researcher' and not upload):
                        return True, id_
                    else:
                        if upload:
                            option = "Upload"
                        else:
                            option = "Download"
                        raise DeliveryOptionException("Chosen upload/download "
                                                      "option not granted. "
                                                      f"You chose: '{option}'. "
                                                      "For help: 'dp_api --help'")


# VALIDATE API OPTIONS - ALREADY IN CODE
def validate_api_options(config: str, username: str, password: str, project: str,
                         pathfile: str, data: tuple) -> (str, str, str):
    """Checks if all required options are entered etc."""

    # All credentials entered? Exception raised if not.
    username, password, project = verify_user_credentials(config=config,
                                                          username=username,
                                                          password=password,
                                                          project=project)

    # Data to be uploaded entered? Exception raised if not.
    if not data and not pathfile:
        raise DeliveryPortalException(
            "No data to be uploaded. Specify individual files/folders using "
            "the --data/-d option one or more times, or the --pathfile/-f. "
            "For help: 'dp_api --help'"
        )

    return username, password, project
	

# GET FILESIZE
def get_filesize(filename: str) -> (int):
    """Returns file size"""

    return os.stat(filename).st_size


# GET PASSSPHRASE 
def get_passphrase():
    """Gets passphrase for private key encryption"""

    return "thisisapassphrasethatshouldbegeneratedsomehow"


# UNCLEAR 
def new_dir(filename: str, sub_dir: str, temp_dir: str, operation: str) -> (str):
"""Checks which dir to place file in"""

ext = ""
if operation == "compression":
	ext = ".gzip"
elif operation == "encryption":
	ext = ".c4gh"
else:
	pass    # Non allowed operation

if sub_dir == "":
	return f"{temp_dir}/{filename}{ext}"
else:
	return f"{sub_dir}/{filename}{ext}"


# CHECKS IF NGS TYPE - ALREADY IN CODE
def ngs_type(extension: str):
    """Checks if the file is of ngs type"""

    mime = ""
    if extension == "": 
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

    return mime


# STREAM CHUNKS 
def stream_chunks(file_handle, chunk_size):
    """Reads file and returns (streams) the content in chunks"""

    try:
        for chunk in iter(lambda: file_handle.read(chunk_size), b''):
            yield chunk
    except StreamingError as se:
        yield "error", f"Could not yield chunk: {se}"


# HANDLE FOLDERS
def process_folder(folder: str, s3_resource, thepool, user: dict, temp_dir: str, sub_dir: str = "") -> (dict):
    """Handles processing of folders. 
    Opens folders and redirects to file processing function. 

    Args: 
        folder: Path to folder
        temp_dir: Temporary directory
        sub_dir: Current sub directory within temp_dir
        s3_resource: 

    Returns: 
        dict: Information abut final files, checksums, errors etc.

    """

    result_dict = {folder: list()}   # Dict for saving paths and hashes

    # Iterate through all folders and files recursively
    for path, dirs, files in os.walk(folder):
        for file in sorted(files):  # For all files in folder root
            # Compress files and add to dict
            # result_dict[folder].append(process_file(file=os.path.join(path, file),
            #                                         temp_dir=temp_dir,
                                                    # sub_dir=sub_dir))
            process_file(file=os.path.join(path, file),
                         s3_resource=s3_resource,
                         user=user,
                         temp_dir=temp_dir,
                         sub_dir=sub_dir)
        for dir_ in sorted(dirs):   # For all subfolders in folder root
            # "Open" subfolder folder (the current method, recursive)
            result_dict[folder].append(process_folder(folder=os.path.join(path, dir_),
                                                      s3_resource=s3_resource,
                                                      user=user,
                                                      temp_dir=temp_dir,
                                                      sub_dir=sub_dir))

            # Create folder in s3 bucket
            # code here
        break

    return result_dict

# IN PROCESS_FILE

    is_compressed = False
    is_encrypted = False

    encryption_algorithm = ""               # Which package/algorithm

    hash_original = ""
    hash_compressed = ""
    hash_encrypted = ""

    mime, ext, is_compressed, \
        compression_algorithm = file_type(file)   # Check mime type

# 20200226 - refactoring to classes 

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


# progress bar

# class ProgressPercentage(object):

#     def __init__(self, filename, filesize):
#         self._filename = filename
#         self._size = filesize
#         self._seen_so_far = 0
#         self._lock = threading.Lock()

#     def __call__(self, bytes_amount):
#         # To simplify, assume this is hooked up to a single filename
#         with self._lock:
#             self._seen_so_far += bytes_amount
#             percentage = (self._seen_so_far / self._size) * 100
#             print(f"\r{self._filename}  {self._seen_so_far} / "
#                              f"{self._size}  ({percentage:.2f}%)")
#             #sys.stdout.flush()


# Default configs:
        # multipart_threshold = 8388608 (8 MB) - multipart uploads/downloads
        #                                           automatically triggered
        # max_concurrency = 10 - max number of threads used to perform transfer
        #                           reduce bandwidth usage -> reduce value
        # multipart_chunksize = 8388608 (8 MB) - partition size for a multipart
        #                                           transfer, chunk size
        # num_download_attempts = 5 - number of times retried upon errors
        # max_io_queue = 100 - max amount of read parts queued in memory
        # io_chunksize = 262144 (256 KB) - max size of each chunk in io queue
        # use_threads = True - threads will be used when performing S3 transfer
        # config = TransferConfig(max_concurrency=10)

# 20200519 -- check if item exist in bucket
        # response = self.resource.meta.client.list_objects_v2(
        #     Bucket=self.bucket.name,
        #     Prefix=key,
        # )

        # print("Key: ", key)
        # matching_paths = [path['Key'] for path in response.get('Contents', [])
        #                   if (path['Key'].startswith(key)
        #                   and path['Size'] != 0)]

        #  if matching_paths:
        #     return True, matching_paths
        # else:
        #     return False, matching_paths

# File or folder handling in put 
 # elif delivery.data[path]['file']:
                #     path_from_base = delivery.get_bucket_path(file=path)

                #     exists, _ = delivery.s3.file_exists_in_bucket(
                #         str(path_from_base / file.name))
                #     if exists:
                #         file_dict[file] = {"Error": "Exists"}
                #         continue  # moves on to next file

                #     # get recipient public key
                #     recip_pub = delivery.get_recipient_key()

                #     # Prepare files for upload incl hashing etc
                #     p_future = pool_exec.submit(key.prep_upload,
                #                                 path,
                #                                 recip_pub,
                #                                 delivery.tempdir,
                #                                 path_from_base)
                #     pools.append(p_future)
                #     file_dict[path] = {"path_base": None,
                #                        "path_from_base": path_from_base,
                #                        "hash": "",
                #                        "bucket_path": path_from_base}


#  CREATING FOLDER IN TEMPDIR FILES      
#  # tempdir_files = tempdir[1]  # Path to temporary delivery file folder

        # filedir = None
        # if isinstance(tempdir_files, Path):
        #     filedir = tempdir_files / path_from_base
        #     if not filedir.exists():
        #         try:
        #             original_umask = os.umask(0)
        #             filedir.mkdir(parents=True)
        #         except IOError as ioe:
        #             sys.exit(f"Could not create folder {filedir}: {ioe}")
        #         finally:
        #             os.umask(original_umask)


# checking if file is path and logging exception
if not delivery.data[path]:
                    CLI_LOGGER.exception(f"Path type {path} not identified."
                                         "Have you entered the correct path?")
                    continue    # Move on to next file

# Directory path 
# All subfolders from entered directory to file
                directory_path = fh.get_root_path(
                    file=path,
                    path_base=delivery.data[path]['path_base']
                )
                CLI_LOGGER.debug(f"{path} -- directory path: {directory_path}")

# Get content info -- if dir
  # elif item.is_dir():
                #     folder_file_info = {}

                #     # Check if compressed archive first
                #     '''here'''

                #     # if not compressed archive check files
                #     for file in self.data[item]['contents']:
                #         proceed, compressed, algorithm, new_file = \
                #             self.do_file_checks(
                #                 file=file,
                #                 file_info=self.data[item]['contents'][file]
                #             )
                #         self.logger.debug(f"\nfile: {file}\t compressed: {compressed}"
                #                           f"\t algorithm: {algorithm}\t"
                #                           f"new file name: {new_file}")
                #         if proceed:
                #             folder_file_info[file] = {"compressed": compressed,
                #                                       "algorithm": algorithm,
                #                                       "new_file": new_file}
                #         else:
                #             return proceed

                #     for file in self.data[item]['contents']:
                #         self.data[item]['contents'][file].update(
                #             folder_file_info[file]
                #         )

####### 1ST JULY 2020
# def update_dir(old_dir, new_dir):
#     '''Update file directory and create folder'''

#     try:
#         original_umask = os.umask(0)
#         updated_dir = old_dir / new_dir
#         if not updated_dir.exists():
#             updated_dir.mkdir(parents=True)
#     except IOError as ioe:
#         sys.exit(f"Could not create folder: {ioe}")
#     finally:
#         os.umask(original_umask)

#     return updated_dir

###### 1ST JULY 2020
# def files_in_bucket(self, key: str):
    #     '''Checks if the current file already exists in the specified bucket.
    #     If so, the file will not be uploaded.

    #     Args:
    #         s3_resource:    Boto3 S3 resource
    #         bucket:         Name of bucket to check for file
    #         key:            Name of file to look for

    #     Returns:
    #         bool:   True if the file already exists, False if it doesnt

    #     '''
    #     # If extension --> file, if not --> folder (?)
    #     folder = (len(key.split(os.extsep)) == 1)

    #     if folder:
    #         if not key.endswith(os.path.sep):  # path is a folder
    #             key += os.path.sep

    #     object_summary_iterator = self.bucket.objects.filter(Prefix=key)
    #     return object_summary_iterator
    #     # for o in object_summary_iterator:
    #     #     yield o

####### 1ST JULY 2020
 # def prep_upload(self, file: str, recip_pub, filedir, path_from_base):
    #     '''Prepares the files for upload'''

    #     # hash
    #     _, checksum = gen_hmac(file=file)

    #     # encrypt
    #     encrypted_file = filedir / Path(file.name + ".c4gh")
    #     print("encrypting file", encrypted_file)
    #     try:
    #         original_umask = os.umask(0)
    #         with file.open(mode='rb') as infile:
    #             with encrypted_file.open(mode='ab+') as outfile:
    #                 lib.encrypt(keys=[(0, self.seckey, recip_pub)],
    #                             infile=infile,
    #                             outfile=outfile)
    #     except EncryptionError as ee:
    #         return file, "Error", ee
    #     finally:
    #         os.umask(original_umask)

    #     return file, encrypted_file, checksum

    # DATA DELIVERER - 20200709!!
    # def do_file_checks(self, file: Path, directory_path, suffixes) -> \
    #         (bool, bool, str, str):
    #     '''Checks if file is compressed and if it has already been delivered.

    #     Args:
    #         file (Path):       Path to file

    #     Returns:
    #         tuple:  Information on if the file is compressed, whether or not
    #                 to proceed with the delivery of the file, and the file path
    #                 after (future) processing.

    #             bool:   True if delivery should proceed for file
    #             bool:   True if file is already compressed
    #             str:    Bucketfilename -- File path with new suffixes
    #             str:    Error message, "" if none
    #     '''

    #     # Set file check as in progress
    #     # self.set_progress(item=file, check=True, started=True)

    #     # Variables ############################################### Variables #
    #     proc_suff = ""      # Saves final suffixes
    #     # ------------------------------------------------------------------- #

    #     # Check if compressed
    #     compressed, error = is_compressed(file)
    #     if error != "":
    #         return False, compressed, "", error

    #     # If file not compressed -- add zst (Zstandard) suffix to final suffix
    #     if not compressed:
    #         # Warning if suffixes are in magic dict but file "not compressed"
    #         if set(suffixes).intersection(set(MAGIC_DICT)):
    #             self.LOGGER.warning(f"File '{file}' has extensions belonging "
    #                                 "to a compressed format but shows no "
    #                                 "indication of being compressed. Not "
    #                                 "compressing file.")

    #         proc_suff += ".zst"     # Update the future suffix
    #         # self.LOGGER.debug(f"File: {file} -- Added suffix: {proc_suff}")
    #     elif compressed:
    #         self.LOGGER.warning(f"File '{file}' shows indication of being "
    #                             "in a compressed format. "
    #                             "Not compressing the file.")

    #     proc_suff += ".ccp"     # ChaCha20 (encryption format) extension added
    #     # self.LOGGER.debug(f"File: {file} -- Added suffix: {proc_suff}")

    #     # Path to file in temporary directory after processing, and bucket
    #     # after upload, >>including file name<<
    #     bucketfilename = str(directory_path /
    #                          Path(file.name + proc_suff))
    #     # self.LOGGER.debug(f"File: {file}\t Bucket path: {bucketfilename}")

    #     # If file exists in DB -- cancel delivery of file
    #     with DatabaseConnector('project_db') as project_db:
    #         if bucketfilename in project_db[self.project_id]['files']:
    #             error = f"File '{file}' already exists in the database. "
    #             self.LOGGER.warning(error)
    #             return False, compressed, bucketfilename, error

    #     # If file exists in S3 bucket -- cancel delivery of file
    #     with S3Connector(bucketname=self.bucketname, project=self.s3project) \
    #             as s3:
    #         # Check if file exists in bucket already
    #         in_bucket, error = s3.file_exists_in_bucket(bucketfilename)
    #         # self.LOGGER.debug(f"File: {file}\t In bucket: {in_bucket}")

    #         if in_bucket:  # If the file is already in bucket
    #             error = (f"{error}\nFile '{file.name}' already exists in "
    #                      "bucket, but does NOT exist in database. " +
    #                      "Delivery cancelled, contact support.")
    #             self.LOGGER.critical(error)
    #             return False, compressed, bucketfilename, error

    #     # Proceed with delivery and return info on file
    #     return True, compressed, bucketfilename, error