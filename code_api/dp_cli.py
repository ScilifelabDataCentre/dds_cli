"""

"""

# IMPORTS ############################################################ IMPORTS #

from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from cryptography.hazmat.primitives import hashes, hmac
from cryptography.hazmat.backends import default_backend
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
import datetime
from itertools import chain
from crypt4gh import keys, engine, header
from functools import partial
from getpass import getpass

from code_api.dp_exceptions import AuthenticationError, CouchDBException, \
    CompressionError, DataException, DeliveryPortalException, DeliveryOptionException, \
    EncryptionError, SecurePasswordException


# GLOBAL VARIABLES ########################################## GLOBAL VARIABLES #


# CLASSES ############################################################ CLASSES #

class ECDHKeyPair:
    """Public key pair. 
    Algorithm: Eliptic Curve Diffie-Hellman (Curve25519)"""

    def __init__(self, privatekey: str = "key", publickey: str = "key"):
        """Generates a public key pair"""

        print("key gen")
        cb = partial(get_passphrase)    # Get passphrase for private key enc

        # Directory for storing keys
        key_dir = f"{os.path.abspath(os.getcwd())}/keys"
        if not os.path.exists(key_dir) and not os.path.isdir(key_dir):
            try:
                os.mkdir(key_dir)   # Create "keys" folder if not exists
            except OSError as ose:
                sys.exit(f"The keys folder could not be created:", f"{ose}")

        # Paths to private and public keys
        priv_keyname = f"{key_dir}/{privatekey}.sec"
        pub_keyname = f"{key_dir}/{publickey}.pub"
        for k_ in [priv_keyname, pub_keyname]:
            if os.path.exists(k_):
                try:
                    os.remove(k_)       # Delete old keys
                except OSError as ose:
                    sys.exit(
                        f"The key {k_} exists but could not be deleted: ", f"{ose}")

        try:
            # Generate public key pair, encrypt private key
            keys.generate(seckey=priv_keyname,
                          pubkey=pub_keyname, callback=cb)
        except EncryptionError as ee:
            sys.exit(
                f"The key pair {priv_keyname}/{pub_keyname} could not be generated: ", f"{ee}")
        else:
            try:
                # Import keys, decrypt private key
                self.pub = keys.get_public_key(filepath=pub_keyname)
                self.sec = keys.get_private_key(filepath=priv_keyname,
                                                callback=cb)
            except EncryptionError as ee:
                sys.exit(
                    f"Could not get the keys {priv_keyname} & {pub_keyname}: ", f"{ee}")

    def encrypt(self, file: str, remote_pubkey):
        """Uses the remote public key and the own private key to encrypt a file"""

        encrypted_file = f"{file}.c4gh"   # Name of encrypted file.
        if os.path.exists(encrypted_file):
            try:
                # Remove old encrypted file if exists
                os.remove(encrypted_file)
            except OSError as ose:
                sys.exit(f"The old encrypted file {file} could not be deleted: ",
                         f"{ose}")

        try:
            # Encrypt file
            with open(file=file, mode='rb') as infile:
                with open(file=encrypted_file, mode='wb+') as outfile:
                    # The 0 in keys is the method (only one allowed)
                    engine.encrypt(keys=[(0, self.sec, remote_pubkey)],
                                   infile=infile, outfile=outfile)
        except EncryptionError as ee:
            sys.exit(f"Could not encrypt file {file}: ",
                     f"{ee}")
        else:
            return encrypted_file


# FUNCTIONS ######################################################## FUNCTIONS #

def get_passphrase():
    """Gets passphrase for private key encryption"""

    return "thisisapassphrasethatshouldbegeneratedsomehow"


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


def compress_data(fileorfolder: str):
    """Makes sure that all data is compressed"""

    upload_path = ""
    name = fileorfolder.split('/')[-1]  # File or folder name
    print("Name : ", name)
    mime = file_type(fileorfolder)      # File or folder mime
    print("Mime : ", mime)

    if mime == 'folder':    # If folder
        click.echo(f"~~~~ Compressing directory '{fileorfolder}'...")
        try:
            upload_path = compress_folder(
                dir_path=fileorfolder, prev_path="")
        except CompressionError as ce:
            pass
            # continue    # Move on to next file/folder
        else:
            click.echo(f"~~~~ Compression completed! Zip archive: \
                '{next(iter(upload_path))}'")
            return upload_path

    else:                   # If file
        # If compressed file, do not compress, and
        # upload path the original path
        if mime in compression_list():
            upload_path = fileorfolder
        else:
            # If not compressed file, change file to be uploaded
            # and compress
            upload_path = f"{fileorfolder}.gzip"    # Comp file name
            compress_file(fileorfolder, upload_path)
            return upload_path


def compress_file(original: str, compressed: str) -> None:
    """Compresses file using gzip"""

    if os.path.exists(compressed):
        try:
            os.remove(compressed)   # Delete compressed file if exists
        except OSError as ose:
            sys.exit(f"Compressed file {compressed} already "
                     "exists, and could not be removed: ", f"{ose}")
    try:
        # Compress file 
        with open(original, 'rb') as pathin:
            with gzip.open(compressed, 'wb') as pathout:
                shutil.copyfileobj(pathin, pathout)
    except CompressionError as ce:
        sys.exit(f"Could not compress the file {original}: {ce}")


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


def compression_list():
    """Returns a list of compressed-format mime types"""

    extlist = ['epub+zip', 'zip', 'x-tar', 'x-rar-compressed', 'gzip', 'x-bzip2',
               'x-7z-compressed', 'x-xz', 'vnd.ms-cab-compressed', 'x-unix-archive', 'x-compress', 'x-lzip']

    return [f'application/{ext}' for ext in extlist]


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
                if user_db[id_]['password_hash'] != password:
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


def gen_hmac(filepath: str) -> str:
    """Generates HMAC for file"""

    key = b"ThisIsTheSuperSecureKeyThatWillBeGeneratedLater"
    h = hmac.HMAC(key, hashes.SHA256(), backend=default_backend())

    with open(filepath, 'rb') as f:
        for compressed_chunk in iter(lambda: f.read(16384), b''):
            h.update(compressed_chunk)
        return h.finalize()


def get_filesize(filename: str) -> int:
    """Returns file size"""

    return os.stat(filename).st_size


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

    if os.path.isdir(fpath):
        return "folder"
    else:
        kind = filetype.guess(fpath)    # Guess file type
        if kind is not None:            # If guess successful
            return kind.mime            # Return mime type
        else:
            # Check if clumped folders (tar or zipped)
            if tarfile.is_tarfile(fpath):
                return "application/tar"
            elif zipfile.is_zipfile(fpath):
                return "application/zip"
            else:
                # If no guess and not clumped folders
                # check file extensions
                extension = os.path.splitext(fpath)[1]
                if extension in (".txt"):
                    return "file/text"
                elif extension in (".csv"):
                    return "file/csv"
                elif extension in (".abi", ".ab1"):
                    return "ngs-data/abi"
                elif extension in (".embl"):
                    return "ngs-data/embl"
                elif extension in (".clust", ".cw", ".clustal"):
                    return "ngs-data/clustal"
                elif extension in (".fa", ".fasta", ".fas", ".fna", ".faa", ".afasta"):
                    return "ngs-data/fasta"
                elif extension in (".fastq", ".fq"):
                    return "ngs-data/fastq"
                elif extension in (".gbk", ".genbank", ".gb"):
                    return "ngs-data/genbank"
                elif extension in (".paup", ".nexus"):
                    return "ngs-data/nexus"
                else:
                    click.echo("Could not determine file format.")
                    return None


def process_file(file: str, sensitive: bool = True, prev_path: str = "") -> dict:
    """Handles file specific compression, hashing and encryption"""

    fname = file.split('/')[-1]     # Get file or folder name
    mime = file_type(file)          # Check mime type
    upload_path = ""                # Latest file generated

    # Check if compressed format
    if mime in compression_list():
        # If compressed save original name as path
        upload_path = file
    else:
        # If not compressed perform compression
        # If first (root) folder, create name for root "compressed" folder
        # If subfolder, alter path to be in "compressed" folders
        if prev_path == "":
            upload_path = f"{file}.gzip"
        else:
            upload_path = f"{prev_path}/{file.split('/')[-1]}.gzip"

        ### Compress file ###
        compress_file(original=file, compressed=upload_path)

    ### Generate file checksum. ###
    hash_file = gen_hmac(upload_path).hex()

    ### Encrypt file ###
    # Generate keys
    researcher_kp = ECDHKeyPair(
        privatekey="researcher", publickey="researcher")
    facility_kp = ECDHKeyPair(privatekey="facility", publickey="facility")

    # Encrypt
    encrypt_path = facility_kp.encrypt(
        file=upload_path, remote_pubkey=researcher_kp.pub)

    # Generate encrypted file checksum
    hash_enc = gen_hmac(encrypt_path).hex()

    return {upload_path: hash_file}, {encrypt_path: hash_enc}


def process_folder(folder: str, sensitive: bool = True, prev_path: str = ""):
    """Handles folder specific compression, hashing, and encryption"""

    comp_path = ""      # Path to "compressed" folder
    if prev_path == "":                 # If root folder
        comp_path = f"{folder}_comp"    # path is the current path + comp
    else:   # If subfolder alter path to be in new folder
        comp_path = f"{prev_path}/{folder.split('/')[-1]}_comp"

    result_dict = {comp_path: list()}   # Dict for saving paths and hashes

    if not os.path.exists(comp_path):
        try:
            os.mkdir(comp_path)     # Create folder if doesn't exist
        except OSError as ose:
            sys.exit(f"Could not create folder '{comp_path}': {ose}")

    # Iterate through all folders and files recursively
    for path, dirs, files in os.walk(folder):
        for file in sorted(files):  # For all files in folder root
            # Compress files and add to dict
            result_dict[comp_path].append(process_file(file=os.path.join(path, file),
                                                       sensitive=sensitive,
                                                       prev_path=comp_path))
        for dir_ in sorted(dirs):   # For all subfolders in folder root
            # "Open" subfolder folder (the current method, recursive)
            result_dict[comp_path].append(process_folder(folder=os.path.join(path, dir_),
                                                         sensitive=sensitive,
                                                         prev_path=comp_path))
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


def secure_password_hash(password):
    """Generates secure password hash"""

    return hashlib.sha256(password.encode('utf-8')).hexdigest()


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
                    secure_password_hash(credentials['password']), \
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
                    secure_password_hash(password), \
                    project


# MAIN ################################################################## MAIN #

@click.group()
def cli():
    click.echo("CLI group thing")


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

    ### Check if the data is compressed ###
    for path in data:
        if os.path.isfile(path):    # <---- FILES
            upload_path[path] = process_file(file=path,
                                             sensitive=sensitive)
        elif os.path.isdir(path):   # <---- FOLDERS
            upload_path[path] = process_folder(folder=path,
                                               sensitive=sensitive)
        else:                       # <---- TYPE UNKNOWN
            sys.exit(f"Path type {path} not identified."
                     "Have you entered the correct path?")

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
