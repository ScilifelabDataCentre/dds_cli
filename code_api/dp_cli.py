"""

"""

# IMPORTS ############################################################ IMPORTS #

import click
import couchdb
import sys
import hashlib
import os
import filetype
import datetime
from itertools import chain

import gzip
import zlib
import zipfile
import shutil

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, hmac
from Crypto.Random import get_random_bytes
from Crypto.Cipher import AES


# GLOBAL VARIABLES ########################################## GLOBAL VARIABLES #

# EXCEPTION CLASSES ######################################## EXCEPTION CLASSES #

class CouchDBException(Exception):
    """Custom exception class. Handles errors in database operations."""

    def __init__(self, msg: str):
        """Passes message from exception call to the base class __init__."""

        super().__init__(msg)


class DeliveryPortalException(Exception):
    """Custom exception class. Handles errors regarding Delivery Portal 
    access etc"""

    def __init__(self, msg: str):
        """Passes message from exception call to base class __init__."""
        super().__init__(msg)


class DeliveryOptionException(Exception):
    """Custom exception class. Handles errors regarding data delivery 
    options (s3 delivery) etc."""

    def __init__(self, msg: str):
        """Passes message from exception call to base class __init__."""
        super().__init__(msg)

# CLASSES ############################################################ CLASSES #


class EncryptionKey:
    """Class responsible for encryption key generation
    and other cryptographic processes"""

    def __init__(self, bytes: int = 32):
        """Generates encryption key."""

        # os.urandom is about as random as it gets.
        # To generate >more< truly random >number< from urandom:
        #       random.SystemRandom().random()
        self.key = os.urandom(bytes)


# FUNCTIONS ######################################################## FUNCTIONS #

def check_dp_access(username: str, password: str) -> (bool, str):
    """Check existance of user in database and the password validity."""

    dp_couch = couch_connect()
    user_db = dp_couch['user_db']
    for id_ in user_db:
        if username in user_db[id_]['username']:
            if user_db[id_]['password_hash'] == password:
                return True, id_

    return False, ""


def check_project_access(user: str, project: str) -> bool:
    """Checks the users access to a specific project."""

    proj_couch = couch_connect()
    user_projects = proj_couch['user_db'][user]['projects']

    if project not in set(chain(user_projects['ongoing'], user_projects['finished'])):
        if click.confirm("You do not have access to the specified project" +
                         f"'{project}'.\n Change project?"):
            check_project_access(user, click.prompt("Project ID"))
        else:
            raise DeliveryPortalException(
                "Project access denied. Aborting upload.")
    else:
        '''3. Project has S3 access?'''
        project_info = proj_couch['project_db'][project]['project_info']
        if not project_info['delivery_option'] == "S3":
            raise DeliveryOptionException(
                "The specified project does not have access to S3.")
        else:
            return True, project_info['sensitive']


def compress_file(original: str, compressed: str) -> None:
    """Compresses file using gzip"""

    with open(original, 'rb') as f_in:
        with gzip.open(compressed, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)


def compression_list():
    """Returns a list of compressed-format mime types"""

    extlist = ['epub+zip', 'zip', 'x-tar', 'x-rar-compressed', 'gzip', 'x-bzip2',
               'x-7z-compressed', 'x-xz', 'vnd.ms-cab-compressed', 'x-unix-archive', 'x-compress', 'x-lzip']

    return [f'application/{ext}' for ext in extlist]


def couch_connect():
    """Connect to a couchdb interface."""

    try:
        couch = couchdb.Server('http://delport:delport@localhost:5984/')
    except CouchDBException:
        print("Database login failed.")

    return couch


def couch_disconnect(couch, token):
    """Disconnect from couchdb interface."""

    try:
        couch.logout(token)
    except CouchDBException:
        print("Could not logout from database.")


def decrypt_file(file, newfile, key, chunk, nonce_length: int = 16, mac_length: int = 16):
    """dfdfgdfg"""

    with open(file, 'rb') as enc_file:
        while True:
            nonce = enc_file.read(nonce_length)
            mac = enc_file.read(mac_length)
            if not nonce or not mac:
                break
            cipher = AES.new(key, AES.MODE_GCM, nonce)
            ciphertext = enc_file.read(chunk)
            plaintext = cipher.decrypt_and_verify(ciphertext, mac)
            if not plaintext:
                break
            with open(newfile, 'ab') as dec_file:
                dec_file.write(plaintext)


def encrypt_file(file, newfile, key, chunk):
    """fdgdfgd"""

    with open(file, 'rb') as plaintext_file:
        while True:
            cipher = AES.new(key, AES.MODE_GCM)
            plaintext = plaintext_file.read(chunk)
            if not plaintext:
                break

            ciphertext, tag = cipher.encrypt_and_digest(plaintext)

            with open(newfile, 'ab') as enc_file:
                enc_file.write(cipher.nonce + tag + ciphertext)


def gen_hmac(filepath: str) -> str:
    """Generates HMAC"""

    key = b"ThisIsTheSuperSecureKeyThatWillBeGeneratedLater"
    h = hmac.HMAC(key, hashes.SHA256(), backend=default_backend())

    with open(filepath, 'rb') as f:
        for compressed_chunk in iter(lambda: f.read(16384), b''):
            h.update(compressed_chunk)
        return h.finalize()


def gen_sha512(filename: str, chunk_size: int = 4094) -> str:
    """Generates unique hash."""

    hasher = hashlib.sha3_512()
    with open(filename, "rb") as f:
        for byte_block in iter(lambda: f.read(chunk_size), b""):
            hasher.update(byte_block)

    return hasher.hexdigest()


def get_filesize(filename: str) -> int:
    """Returns file size"""

    return os.stat(filename).st_size


def get_current_time() -> str:
    """Gets the current time and formats for database."""

    now = datetime.datetime.now()

    return f"{now.year}-{now.month}-{now.day} {now.hour}:{now.minute}:{now.second}"


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


def file_type(filename: str) -> str:
    """Guesses file mime based on extension"""

    kind = filetype.guess(filename)
    if kind is not None:
        return kind.mime
    else:
        extension = os.path.splitext(filename)[1]

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


# MAIN ################################################################## MAIN #

@click.command()
@click.option('--upload/--download', default=True, required=True,
              help="Facility upload or user download.")
@click.option('--file', '-f', required=True, multiple=True,
              type=click.Path(exists=True), help='File to upload.')
@click.option('--username', '-u', type=str, help="Delivery Portal username.")
@click.option('--project', '-p', type=str, help="Project to upload files to.")
def upload_files(upload, file: str, username: str, project: str):
    """Main function. Handles file upload.

    * If multiple files, use option multiple times.
    * File name cannot start with "-".

    Example one file:
        "--file /path/to/file.xxx"
    Example multiple files:
        "--file /path/to/file1.xxx --file /path/to/file2.xxx ..." etc.
    """

    upload_path = {}
    hash_dict = {}

    '''1. Facility has DP access?'''
    # Ask for DP username if not entered and associated password
    if not username:
        # username = click.prompt("Enter username\t", type=str)
        username = "facility1"
    # password = click.prompt("Password\t", hide_input=True, confirmation_prompt=True)
    password = hashlib.sha256(b"facility1").hexdigest()

    # Check user access to DP
    click.echo("[*] Verifying Delivery Portal access...")
    access_granted, user_id = check_dp_access(username, password)
    if not access_granted:
        raise DeliveryPortalException(
            "You are not authorized to access the Delivery Portal. Aborting.")
    else:
        click.echo("[**] Access granted!\n")

        '''2. Facility has project access?'''
        '''3. Project has S3 access?'''
        # If project not chosen, ask for project to upload to
        if not project:
            # project = click.prompt("Project to upload files to")
            project = "0372838e2cf1f4a2b869974723002bb7"

        # Check project access
        click.echo("[*] Verifying project access...")
        project_access, sensitive = check_project_access(user_id, project)
        if not project_access:
            raise DeliveryPortalException(
                "Project access denied. Cancelling upload.")
        else:
            click.echo("[**] Project access granted!\n")

            key = b"ThisIsTheSuperSecureKeyThatWillBeGeneratedLater"
            
            '''4. Compressed?'''
            for f_ in file:
                if os.path.isfile(f_):
                    # If the entered path is a file, perform compression on individual file
                    mime = file_type(f_)

                    # If mime is a compressed format: update path
                    # If mime not a compressed format:
                    # -- perform compression on file
                    if mime in compression_list():
                        upload_path[f_] = f_
                    else:
                        '''5. Perform compression'''
                        click.echo(f"~~~~ Compressing file '{f_}'...")
                        upload_path[f_] = f"{f_}.gzip"
                        compress_file(f_, upload_path[f_])
                        click.echo(f"~~~~ Compression completed! Compressed file: '{upload_path[f_]}")

                    '''6. Generate file checksum.'''
                    click.echo("~~~~ Generating HMAC...")
                    hash_dict[f_] = gen_hmac(upload_path[f_]).hex()
                    click.echo("~~~~ HMAC generated!")

                elif os.path.isdir(f_):
                    click.echo(f"[*] Directory: {f_}")

                    # If the entered path is a directory, a zip archive is generated
                    '''5. Perform compression'''
                    click.echo(f"~~~~ Compressing directory '{f_}'...")
                    upload_path[f_] = f"{f_}.zip"
                    shutil.make_archive(f_, 'zip', f_)
                    click.echo(f"~~~~ Compression completed! Zip archive: '{upload_path[f_]}'")

                    '''6. Generate directory checksum.'''
                    click.echo("~~~~ Generating HMAC...")
                    hash_dict[f_] = hash_dir(os.path.abspath(f_), key)
                    click.echo("~~~~ HMAC generated!\n")

                else:
                    raise OSError("Path type not identified.")

                '''7. Sensitive?'''
                if not sensitive:
                    '''12. Upload to non sensitive bucket'''
                else:
                    '''8. Get user public key'''
                    '''9. Generate facility keys'''
                    '''10. Encrypt data'''
                    '''11. Generate checksum'''
                    '''12. Upload to sensitive bucket'''

            # Create file checksums and save in database
            # Save checksum and metadata in db
            # TODO: move this to after upload
            couch = couch_connect()               # Connect to database
            project_db = couch['project_db']      # Get project database
            if project not in project_db:       # Check if project exists in database
                raise CouchDBException(
                    "The specified project is not recorded in the database. Aborting upload.")
            else:                                       # If project exists
                project_doc = project_db[project]       # Get project document
                project_files = project_doc['files']    # Get files

                # Get project sensitive information from database
                if 'project_info' in project_doc and 'sensitive' in project_doc['project_info']:
                    sensitive = project_db[project]['project_info']['sensitive']

                for f_ in file:    # Generate and save checksums
                    try:
                        project_files[f_] = {"size": get_filesize(f_),
                                             "mime": file_type(f_),
                                             "date_uploaded": get_current_time(),
                                             "checksum": gen_sha512(f_)}   # Save checksum in db
                    except CouchDBException:
                        print(f"Could not update file {f_} metadata.")

                try:
                    project_db.save(project_doc)
                except CouchDBException:
                    print(
                        f"Updating project {project} failed. Cancelling upload.")

            # TODO: Encrypt files (ignoring the key stuff atm) + stream to s3 (if possible)
            # TODO: Compress files
            # TODO: Show success message
            # TODO: Delete from database if failed upload
            # TODO: Save metadata to db
            # TODO: Show success message
            # TODO: Generate email to user of interest
