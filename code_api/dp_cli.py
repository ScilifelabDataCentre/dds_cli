"""
Command line interface for Data Delivery Portal
"""

# IMPORTS ############################################################ IMPORTS #

from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from cryptography.hazmat.primitives import hashes, hmac
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
import shutil
import zipfile
import zlib
import tarfile
import gzip
import click
import couchdb
import sys
import hashlib
import os
import filetype
import mimetypes
import datetime
from itertools import chain
import logging
import logging.config

from ctypes import *

from crypt4gh import keys, engine, header
from functools import partial
from getpass import getpass

from code_api.dp_exceptions import AuthenticationError, CouchDBException, \
    CompressionError, DataException, DeliveryPortalException, DeliveryOptionException, \
    EncryptionError, HashException, SecurePasswordException, StreamingError

# CONFIG ############################################################## CONFIG #

logging.config.dictConfig({
    'version': 1,
    'disable_existing_loggers': True,
})

# GLOBAL VARIABLES ########################################## GLOBAL VARIABLES #

COMPRESSED_FORMATS = dict()


# CLASSES ############################################################ CLASSES #


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
            keys.generate(seckey=priv_keyname,
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
                    engine.encrypt(keys=[(0, self.sec, remote_pubkey)],
                                   infile=infile, outfile=outfile)
        except EncryptionError as ee:
            logging.error("Some error message here.")
            error = f"Could not encrypt file {file}: {ee}"
        else:
            logging.info("Some success message here.")

        return encrypted_file, "crypt4gh", error


# FUNCTIONS ######################################################## FUNCTIONS #

def all_data(data_tuple: tuple, data_file: str):
    """Puts all data from tuple and file into one tuple"""

    # If both --data and --pathfile option --> all paths in data tuple
    # If only --pathfile --> reads file and puts paths in data tuple
    try:
        if data_file:
            if os.path.exists(data_file):
                with open(data_file, 'r') as pf:
                    data_tuple += tuple(p for p in pf.read().splitlines())
    except DataException as de:
        sys.exit(f"Could not create data tuple: {de}")
    else:
        return data_tuple


def check_access(username: str, password: str, project: str, upload: bool = True) -> (str, bool):
    """Checks the users access to the delivery portal and the specified project,
    and the projects S3 access"""

    ### Check DP access ###
    access_granted, user_id = dp_access(username=username,
                                        password=password,
                                        upload=upload)
    if not access_granted:
        raise DeliveryPortalException(
            "You are not authorized to access the Delivery Portal. Aborting."
        )
    else:
        ### Check project access ###
        project_access_granted, sensitive = project_access(user=user_id,
                                                           project=project)
        if not project_access_granted:
            raise DeliveryPortalException(
                "Project access denied. Cancelling upload."
            )
        else:
            return user_id, sensitive


def compress_chunk(original_chunk):
    """Compress individual chunks read in a streamed fashion"""

    try:
        yield gzip.compress(data=original_chunk)
    except CompressionError as ce:
        yield "error", f"Compression of chunk failed: {ce}"


def compress_file(original: str, temp_dir: str, sub_dir: str) -> (str, str):
    """Compresses file using gzip"""

    error = ""

    fname = original.split('/')[-1]
    if sub_dir == "":
        compressed = f"{temp_dir}/{fname}.gzip"
    else:
        compressed = f"{sub_dir}/{fname}.gzip"

    try:
        # Compress file
        with open(original, 'rb') as pathin:
            with gzip.open(compressed, 'wb') as pathout:
                shutil.copyfileobj(pathin, pathout)
    except CompressionError as ce:
        logging.error("Some error message here.")
        error = f"Compression failed. Could not compress the file {original}: {ce}"
    else:
        logging.info("Some success message here.")

    return compressed, "gzip", error


def compress_folder(dir_path: str, prev_path: str = "") -> list:
    """Iterates through a folder and compresses each file"""

    comp_path = ""
    # If first (root) folder, create name for root "compressed" folder
    # If subfolder, alter path to be in "compressed" folders
    if prev_path == "":
        comp_path = f"{dir_path}_comp"
    else:
        comp_path = f"{prev_path}/{dir_path.split('/')[-1]}_comp"

    result_dict = {comp_path: list()}   # Add path to upload dict

    if not os.path.exists(comp_path):
        try:
            os.mkdir(comp_path)     # Create comp path
        except OSError as ose:
            print(f"Could not create folder '{comp_path}': {ose}")

    # Iterate through all folders and files recursively
    for path, dirs, files in os.walk(dir_path):
        for file in sorted(files):  # For all files in folder root
            original = os.path.join(path, file)
            compressed = f"{comp_path}/{file}.gzip"
            compress_file(original=original, compressed=compressed)
            result_dict[comp_path].append(compressed)
        for dir_ in sorted(dirs):   # For all folders in folder root
            result_dict[comp_path].append(compress_folder(
                os.path.join(path, dir_), comp_path))
        break

    return result_dict


def compression_dict():
    """Returns a list of compressed-format mime types"""

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


def couch_connect():
    """Connect to a couchdb interface."""

    try:
        couch = couchdb.Server('http://delport:delport@localhost:5984/')
    except CouchDBException as cdbe:
        sys.exit(f"Database login failed. {cdbe}")
    else:
        return couch


def couch_disconnect(couch, token):
    """Disconnect from couchdb interface."""

    try:
        couch.logout(token)
    except CouchDBException:
        print("Could not logout from database.")


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
                if user_db[id_]['password']['hash'] != secure_password_hash(password=password,
                                                                            settings=user_db[id_]['password']['settings']):
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


def generate_header(own_private_key, remote_public_key):
    """Generates crypt4gh format header"""

    encryption_method = 0           # ChaCha20
    session_key = os.urandom(32)    # Key (file)
    cipher = ChaCha20Poly1305(session_key)  # Cipher (file)

    # 'keys' format: (method, own-private-key, remote-public-key)
    keys = [(0, own_private_key, remote_public_key)]

    header_content = header.make_packet_data_enc(encryption_method=encryption_method,
                                                 session_key=session_key)
    header_packets = header.encrypt(packet=header_content,
                                    keys=keys)
    header_bytes = header.serialize(packets=header_packets)

    return header_bytes, cipher


def get_current_time() -> str:
    """Gets the current time and formats for database."""

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


def get_filesize(filename: str) -> int:
    """Returns file size"""

    return os.stat(filename).st_size


def get_passphrase():
    """Gets passphrase for private key encryption"""

    return "thisisapassphrasethatshouldbegeneratedsomehow"


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


def file_type(fpath: str) -> str:
    """Guesses file mime based on extension"""

    mime = None             # file mime
    is_compressed = False
    comp_alg = ""

    if os.path.isdir(fpath):
        return "folder", is_compressed
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
            else:
                mime = ngs_type(extension=extension)

                if mime is None:
                    logging.warning("Some warning message here.")

        return mime, extension, is_compressed, comp_alg


def new_dir(filename: str, sub_dir: str, temp_dir: str, operation: str) -> str:
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


def ngs_type(extension: str):
    """Checks if the file is of ngs type"""

    mime = ""
    if extension in (".abi", ".ab1"):
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


def process_file(file: str, temp_dir: str, sub_dir: str = "", sensitive: bool = True) -> dict:
    """Handles file specific compression, hashing and encryption"""

    is_compressed = False                   # Saves info about compressed or not
    is_encrypted = False                    # Saves info about encrypted or not

    fname = file.split('/')[-1]             # Get file or folder name
    mime, ext, is_compressed, \
        compression_algorithm = file_type(file)   # Check mime type
    latest_path = ""                        # Latest file generated

    encryption_algorithm = ""               # Which package/algorithm

    key = b"SuperSecureHmacKey"

    hash_original = hmac.HMAC(key=key, algorithm=hashes.SHA256(),
                              backend=default_backend())                      # Original/compressed file hash
    hash_compressed = hmac.HMAC(key=key, algorithm=hashes.SHA256(),
                                backend=default_backend())                    # Hash for compressed file
    hash_encrypted = hmac.HMAC(key=key, algorithm=hashes.SHA256(),
                               backend=default_backend())                     # Encrypted file hash

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

            hash_decrypted = try_decryption(encrypted_file=latest_path, keypair=(researcher_kp.sec, facility_kp.pub))
            print(hash_decrypted, hash_original, hash_decrypted == hash_original)
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

    logging.info("Some success message here.")
    return {"Final path": latest_path,
            "Compression": {
                "Compressed": is_compressed,
                "Algorithm": compression_algorithm,
                "Checksum": hash_compressed
            },
            "Encryption": {
                "Encrypted": is_encrypted,
                "Algorithm": encryption_algorithm,
                "Checksum": hash_encrypted
            }
            }


def process_folder(folder: str, temp_dir: str, sub_dir: str = "", sensitive: bool = True):
    """Handles folder specific compression, hashing, and encryption"""

    result_dict = {folder: list()}   # Dict for saving paths and hashes

    # Iterate through all folders and files recursively
    for path, dirs, files in os.walk(folder):
        for file in sorted(files):  # For all files in folder root
            # Compress files and add to dict
            result_dict[folder].append(process_file(file=os.path.join(path, file),
                                                    temp_dir=temp_dir,
                                                    sub_dir=sub_dir,
                                                    sensitive=sensitive))
        for dir_ in sorted(dirs):   # For all subfolders in folder root
            # "Open" subfolder folder (the current method, recursive)
            result_dict[folder].append(process_folder(folder=os.path.join(path, dir_),
                                                      temp_dir=temp_dir,
                                                      sub_dir=sub_dir,
                                                      sensitive=sensitive))
        break

    return result_dict


def project_access(user: str, project: str) -> (bool, bool):
    """Checks the users access to a specific project."""

    proj_couch = couch_connect()    # Connect to database
    user_projects = proj_couch['user_db'][user]['projects']

    # If the specified project is not present in the users project list
    # raise exception and quit
    if project not in proj_couch['project_db']:
        raise CouchDBException(f"The project {project} does not exist.")
    else:
        if project not in set(chain(user_projects['ongoing'], user_projects['finished'])):
            raise DeliveryOptionException("You do not have access to the specified project "
                                          f"{project}. Aborting upload.")
        else:
            # If the project exists but does not have any 'project_info'
            # raise exception and quit
            if 'project_info' not in proj_couch['project_db'][project]:
                raise CouchDBException("'project_info' not in "
                                       "database 'project_db'.")
            else:
                ### Does the project have S3 access (S3 delivery as option)? ###
                # If the project exists, there is project information,
                # but the project delivery option is not S3, raise except and quit
                project_info = proj_couch['project_db'][project]['project_info']
                if not project_info['delivery_option'] == "S3":
                    raise DeliveryOptionException("The specified project does "
                                                  "not have access to S3.")
                else:
                    # If the project exists and the chosen delivery option is S3
                    # grant project access and get project information
                    return True, project_info['sensitive']


def secure_password_hash(password: str, settings: str) -> str:
    """Generates secure password hash"""

    # n value for fast interactive login
    split_settings = settings.split("$")
    for i in [0, 1, 2]:
        split_settings[i] = int(split_settings[i])

    return hashlib.scrypt(password=password.encode('utf-8'),
                          salt=bytes.fromhex(split_settings[-1]),
                          n=split_settings[0],
                          r=split_settings[1],
                          p=split_settings[2]).hex()


def stream_chunks(file_handle, chunk_size):
    """Reads file and returns (streams) the content in chunks"""

    try:
        for chunk in iter(lambda: file_handle.read(chunk_size), b''):
            yield chunk
    except StreamingError as se:
        yield "error", f"Could not yield chunk: {se}"


def try_decryption(encrypted_file: str, keypair):
    """Tests decryption of encrypted c4gh file"""

    with open(encrypted_file, 'rb') as ef:
        with open(f"{encrypted_file}.decrypted", 'wb') as df:
            engine.decrypt(keys=[(0, keypair[0], keypair[1])], infile=ef,
                        outfile=df)

    # NOT WORKING #
    hash_decrypted = hmac.HMAC(key=key, algorithm=hashes.SHA256(),
                                               backend=default_backend())              
    hash_decrypted = gen_hmac(filepath=f"{encrypted_file}.decrypted",
                              chunk_size=65536, hash_=hash_decrypted)

    return hash_decrypted


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


def verify_user_credentials(config: str, username: str, password: str, project: str) -> (str, str, str):
    """Checks that the correct options and credentials are entered"""

    credentials = dict()

    # If none of username, password and config options are set
    # raise exception and quit execution
    if all(x is None for x in [username, password, config]):
        raise DeliveryPortalException("Delivery Portal login credentials "
                                      "not specified. Enter --username/-u "
                                      "AND --password/-pw, or --config/-c. "
                                      "For help: 'dp_api --help'.")
    else:
        if config is not None:              # If config file entered
            if os.path.exists(config):
                with open(config, 'r') as cf:
                    for line in cf:
                        # Get username, password and project ID
                        (cred, val) = line.split(':')
                        credentials[cred] = val.rstrip()

                # Check that all credentials are entered and quit if not
                for c in ['username', 'password', 'project']:
                    if c not in credentials:
                        raise DeliveryPortalException("The config file does not "
                                                      f"contain: '{c}'.")
                return credentials['username'], \
                    credentials['password'], \
                    credentials['project']
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
                return username, \
                    password, \
                    project


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
def put(config: str, username: str, password: str, project: str,
        pathfile: str, data: tuple):
    """Handles file upload. """

    upload_path = dict()    # format: {original-file:file-to-be-uploaded}
    hash_dict = dict()      # format: {original-file:hmac}
    failed = dict()         # failed file/folder uploads

    # Check that all CLI options are correctly entered
    username, password, project = validate_api_options(config=config,
                                                       username=username,
                                                       password=password,
                                                       project=project,
                                                       pathfile=pathfile,
                                                       data=data)

    # Check user access to DP and project, and project to S3 delivery option
    user_id, sensitive = check_access(username=username, password=password,
                                      project=project, upload=True)

    # Put all data in one tuple
    data = all_data(data_tuple=data, data_file=pathfile)

    # Create temporary folder with timestamp and all subfolders
    timestamp = get_current_time().replace(" ", "_").replace(":", "-")
    temp_dir = f"{os.getcwd()}/DataDelivery_{timestamp}"
    dirs = tuple(p for p in [temp_dir,
                             f"{temp_dir}/files",
                             f"{temp_dir}/keys",
                             f"{temp_dir}/meta",
                             f"{temp_dir}/logs"]) + \
        tuple(f"{temp_dir}/files/{p.split('/')[-1].split('.')[0]}"
              for p in data)
    for d_ in dirs:
        try:
            os.mkdir(d_)
        except OSError as ose:
            sys.exit(f"The directory '{d_}' could not be created: {ose}"
                     "Cancelling delivery.")

    logging.basicConfig(filename=f"{temp_dir}/logs/data-delivery.log",
                        level=logging.DEBUG)
    logging.debug("debug")
    logging.info("info")
    logging.warning("warning")
    logging.error("error")
    logging.critical("critical")

    ### Check if the data is compressed ###
    for path in data:
        sub_dir = f"{temp_dir}/files/{path.split('/')[-1].split('.')[0]}"
        if os.path.isfile(path):    # <---- FILES
            upload_path[path] = process_file(file=path,
                                             temp_dir=temp_dir,
                                             sub_dir=sub_dir,
                                             sensitive=sensitive)
        elif os.path.isdir(path):   # <---- FOLDERS
            upload_path[path] = process_folder(folder=path,
                                               temp_dir=temp_dir,
                                               sub_dir=sub_dir,
                                               sensitive=sensitive)
        else:                       # <---- TYPE UNKNOWN
            sys.exit(f"Path type {path} not identified."
                     "Have you entered the correct path?")

    print(upload_path)

    ### Upload process here ###

    ### Database update here ###


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
    """Handles file download. """

    click.echo("download function")


# sys.exit()
#             # Create file checksums and save in database
#             # Save checksum and metadata in db
#             # TODO: move this to after upload
#             couch = couch_connect()               # Connect to database
#             project_db = couch['project_db']      # Get project database
#             if project not in project_db:       # Check if project exists in database
#                 raise CouchDBException(
#                     "The specified project is not recorded in the database. Aborting upload.")
#             else:                                       # If project exists
#                 project_doc = project_db[project]       # Get project document
#                 project_files = project_doc['files']    # Get files

#                 # Get project sensitive information from database
#                 if 'project_info' in project_doc and 'sensitive' in project_doc['project_info']:
#                     sensitive = project_db[project]['project_info']['sensitive']

#                 for path in data:    # Generate and save checksums
#                     try:
#                         project_files[path] = {"size": get_filesize(path),
#                                                "mime": file_type(path),
#                                                "date_uploaded": get_current_time(),
#                                                "checksum": "hashhere"}   # Save checksum in db
#                     except CouchDBException:
#                         print(f"Could not update {path} metadata.")

#                 try:
#                     project_db.save(project_doc)
#                 except CouchDBException:
#                     print(
#                         f"Updating project {project} failed. Cancelling upload.")
