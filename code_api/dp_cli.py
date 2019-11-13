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
import gzip
import click
import couchdb
import sys
import hashlib
import os
import filetype
import datetime
from itertools import chain

from code_api.dp_exceptions import AuthenticationError, CouchDBException, \
    DeliveryPortalException, DeliveryOptionException, SecurePasswordException


# GLOBAL VARIABLES ########################################## GLOBAL VARIABLES #


# CLASSES ############################################################ CLASSES #


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

    with open(original, 'rb') as pathin:
        with gzip.open(compressed, 'wb') as pathout:
            shutil.copyfileobj(pathin, pathout)


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


def gen_hmac(filepath: str) -> str:
    """Generates HMAC"""

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
@click.option('--data', '-d', required=True, multiple=True,
              type=click.Path(exists=True), help="Path to file or folder to upload.")
@click.option('--pathfile', '-f', required=False, multiple=False,
              type=click.Path(exists=True),
              help="Path to file containing all files and folders to be uploaded.")
@click.option('--username', '-u', type=str, help="Delivery Portal username.")
@click.option('--project', '-p', type=str, help="Project to upload files to.")
def upload_files(upload, data: str, pathfile: str, username: str, project: str):
    """Main function. Handles file upload.

    * If multiple files, use option multiple times.
    * File name cannot start with "-".

    Example one file:
        "--data /path/to/file.xxx"
    Example multiple files:
        "--data /path/to/file1.xxx --data /path/to/file2.xxx ..." etc.
    """

    print("Data: ", data)
    print("Path file: ", pathfile)

    upload_path = {}    # format: {original-file:file-to-be-uploaded}
    hash_dict = {}      # format: {original-file:hmac}

    '''1. Facility has DP access?'''
    # Ask for DP username if not entered and associated password
    if not username:
        username = "facility1"  # click.prompt("Enter username\t", type=str)
    password = hashlib.sha256(b"Facility1").hexdigest()     # TODO: In browser?
    # password = click.prompt("Password\t", hide_input=True, confirmation_prompt=True)

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
            for path in data:
                filename = path.split('/')[-1]
                click.echo(f"Filename: {filename}")
                if os.path.isfile(path):
                    # If the entered path is a file, perform compression on individual file
                    mime = file_type(path)

                    # If mime is a compressed format: update path
                    # If mime not a compressed format:
                    # -- perform compression on file
                    if mime in compression_list():
                        upload_path[path] = filename
                    else:
                        '''5. Perform compression'''
                        click.echo(f"~~~~ Compressing file '{path}'...")
                        upload_path[path] = f"{filename}.gzip"
                        compress_file(path, upload_path[path])
                        click.echo(
                            f"~~~~ Compression completed! Compressed file: '{upload_path[path]}")

                    '''6. Generate file checksum.'''
                    click.echo("~~~~ Generating HMAC...")
                    hash_dict[path] = gen_hmac(upload_path[path]).hex()
                    click.echo("~~~~ HMAC generated!")

                elif os.path.isdir(path):
                    click.echo(f"[*] Directory: {path}")

                    # If the entered path is a directory, a zip archive is generated
                    '''5. Perform compression'''
                    click.echo(f"~~~~ Compressing directory '{path}'...")
                    upload_path[path] = f"{path}.zip"
                    shutil.make_archive(path, 'zip', path)
                    click.echo(
                        f"~~~~ Compression completed! Zip archive: '{upload_path[path]}'")

                    '''6. Generate directory checksum.'''
                    click.echo("~~~~ Generating HMAC...")
                    hash_dict[path] = hash_dir(os.path.abspath(path), key)
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

                for path in data:    # Generate and save checksums
                    try:
                        project_files[path] = {"size": get_filesize(path),
                                               "mime": file_type(path),
                                               "date_uploaded": get_current_time(),
                                               "checksum": "hashhere"}   # Save checksum in db
                    except CouchDBException:
                        print(f"Could not update {path} metadata.")

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
