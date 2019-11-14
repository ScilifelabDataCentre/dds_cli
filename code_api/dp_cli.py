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
from crypt4gh import keys
from functools import partial
from getpass import getpass

from code_api.dp_exceptions import AuthenticationError, CouchDBException, \
    CompressionError, DeliveryPortalException, DeliveryOptionException, \
    SecurePasswordException


# GLOBAL VARIABLES ########################################## GLOBAL VARIABLES #


# CLASSES ############################################################ CLASSES #


# FUNCTIONS ######################################################## FUNCTIONS #

def compress_file(original: str, compressed: str) -> None:
    """Compresses file using gzip"""

    with open(original, 'rb') as pathin:
        with gzip.open(compressed, 'wb') as pathout:
            shutil.copyfileobj(pathin, pathout)


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

    try:
        os.mkdir(comp_path)     # Create comp path
    except OSError as ose:
        print(f"Could not create folder '{comp_path}': {ose}")
    else:
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
        user_db = couch_connect()['user_db']
    except CouchDBException as cdbe:
        sys.exit(f"Could not collect database 'user_db'. {cdbe}")
    else:
        for id_ in user_db:
            if username != user_db[id_]['username']:
                raise CouchDBException("Invalid username, "
                                       "user does not exist in database. ")
            else:
                if user_db[id_]['password_hash'] != password:
                    raise DeliveryPortalException("Wrong password. "
                                                  "Access to Delivery Portal"
                                                  "denied.")
                else:
                    if (user_db[id_]['role'] == 'facility' and upload) or \
                            (user_db[id_]['role'] == '' and not upload):
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


def project_access(user: str, project: str) -> bool:
    """Checks the users access to a specific project."""

    proj_couch = couch_connect()
    user_projects = proj_couch['user_db'][user]['projects']

    if project not in set(chain(user_projects['ongoing'], user_projects['finished'])):
        raise DeliveryOptionException("You do not have access to the specified project "
                                      f"{project}. Aborting upload.")
    else:
        if 'project_info' not in proj_couch['project_db'][project]:
            raise CouchDBException("'project_info' not in "
                                   "database 'project_db'.")
        else:
            project_info = proj_couch['project_db'][project]['project_info']
            if not project_info['delivery_option'] == "S3":
                raise DeliveryOptionException("The specified project does "
                                              "not have access to S3.")
            else:
                return True, project_info['sensitive']


def secure_password_hash(password):
    """Generates secure password hash"""

    # TODO -- currently not secure. Use scrypt or similar.

    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def validate_api_options(username, password, config, project):
    """Checks that the correct options and credentials are entered"""

    credentials = dict()

    if all(x is None for x in [username, password, config]):
        raise DeliveryPortalException("Delivery Portal login credentials "
                                      "not specified. Enter --username/-u "
                                      "AND --password/-pw, or --config/-c. "
                                      "For help: 'dp_api --help'.")
    else:
        if config is not None:
            if os.path.exists(config):
                with open(config, 'r') as cf:
                    for line in cf:
                        (cred, val) = line.split(':')
                        credentials[cred] = val.rstrip()

                for c in ['username', 'password', 'project']:
                    if c not in credentials:
                        raise DeliveryPortalException("The config file does not "
                                                      f"contain: '{c}'.")
                return credentials['username'], \
                    secure_password_hash(credentials['password']), \
                    credentials['project']
        else:
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

@click.command()
@click.option('--upload/--download', required=True, default=True,
              help="Facility upload or user download.")
@click.option('--data', '-d', required=False, multiple=True,
              type=click.Path(exists=True), help="Path to file or folder to upload.")
@click.option('--pathfile', '-f', required=False, multiple=False,
              type=click.Path(exists=True), help="Path to file containing all files and folders to be uploaded.")
@click.option('--username', '-u', required=False,
              type=str, help="Delivery Portal username.")
@click.option('--password', '-pw', required=False,
              type=str, help="Delivery Portal password.")
@click.option('--project', '-p', required=False,
              type=str, help="Project to upload files to.")
@click.option('--config', '-c', required=False,
              type=click.Path(exists=True),
              help="Path to config file containing e.g. username, password, project id, etc.")
def upload_files(upload: bool, data: str, pathfile: str, username: str, password: str,
                 project: str, config: str):
    """Main function. Handles file upload.

    * If multiple files, use option multiple times.
    * File name cannot start with "-".

    Example one file:
        "--data /path/to/file.xxx"
    Example multiple files:
        "--data /path/to/file1.xxx --data /path/to/file2.xxx ..." etc.
    """

    upload_path = dict()    # format: {original-file:file-to-be-uploaded}
    hash_dict = dict()      # format: {original-file:hmac}
    failed = dict()         # failed file/folder uploads
    credentials = dict()    # List of login credentials

    # All credentials entered? Exception raised if not.
    username, password, project = validate_api_options(
        username, password, config, project)

    if not data and not pathfile:
        raise DeliveryPortalException("No data to be uploaded. "
                                      "Specify individual files/folders using "
                                      "the --data/-d option one or more times, "
                                      "or the --pathfile/-f. For help: "
                                      "'dp_api --help'")

    '''1. Facility has DP access?'''
    click.echo("[*] Verifying Delivery Portal access...")
    access_granted, user_id = dp_access(username, password, upload)
    if not access_granted:
        raise DeliveryPortalException(
            "You are not authorized to access the Delivery Portal. Aborting.")
    else:
        click.echo("[**] Access granted!\n")
        sys.exit()

        '''2. Facility has project access?'''
        '''3. Project has S3 access?'''
        click.echo("[*] Verifying project access...")
        project_access_granted, sensitive = project_access(user_id, project)
        if not project_access_granted:
            raise DeliveryPortalException(
                "Project access denied. Cancelling upload.")
        else:
            click.echo("[**] Project access granted!\n")

            key = b"ThisIsTheSuperSecureKeyThatWillBeGeneratedLater"

            # If both --data and --pathfile option --> all paths in data tuple
            # If only --pathfile --> reads file and puts paths in data tuple
            if pathfile:
                if os.path.exists(pathfile):
                    with open(pathfile, 'r') as pf:
                        data += tuple(p for p in pf.read().splitlines())

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
                        click.echo(f"~~~~ Compression completed! Compressed file: \
                            '{upload_path[path]}")

                    '''6. Generate file checksum.'''
                    # TODO: add checks for if the compression failed,
                    # in that case ignore the file
                    click.echo("~~~~ Generating HMAC...")
                    hash_dict[path] = gen_hmac(upload_path[path]).hex()
                    click.echo("~~~~ HMAC generated!\n")

                elif os.path.isdir(path):
                    click.echo(f"[*] Directory: {path}")

                    # If the entered path is a directory, all files in directory are compressed
                    '''5. Perform compression'''
                    click.echo(f"~~~~ Compressing directory '{path}'...")
                    try:
                        upload_path[path] = compress_folder(
                            dir_path=path, prev_path="")
                    except CompressionError as ce:
                        failed[path] = [
                            f"Compression of folder {path} failed.", ce]
                        continue    # Move on to next file/folder
                    else:
                        click.echo(f"~~~~ Compression completed! Zip archive: \
                            '{upload_path[path]}'")

                    '''6. Generate directory checksum.'''
                    # TODO: add checks for if the compression failed,
                    # in that case ignore the file
                    click.echo("~~~~ Generating HMAC...")
                    hash_dict[path] = hash_dir(upload_path[path], key)
                    click.echo("~~~~ HMAC generated!\n")

                else:
                    failed[path] = [f"Path type {path} not identified. \
                                    Have you entered the correct path?",
                                    "No exception raised."]

                '''7. Sensitive?'''
                if not sensitive:
                    '''12. Upload to non sensitive bucket'''
                else:
                    '''8. Get user public key'''
                    ##
                    '''9. Generate facility keys'''
                    cb = partial(getpass, prompt="Passphrase for private key ")
                    keys.generate(seckey=f"/Users/inaod568/Documents/keys/{filename}_facility.sec",
                                  pubkey=f"/Users/inaod568/Documents/keys/{filename}facility.pub", callback=cb)
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
