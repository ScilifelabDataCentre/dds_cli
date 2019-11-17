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
    CompressionError, DeliveryPortalException, DeliveryOptionException, \
    SecurePasswordException


# GLOBAL VARIABLES ########################################## GLOBAL VARIABLES #


# CLASSES ############################################################ CLASSES #


# FUNCTIONS ######################################################## FUNCTIONS #

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
            click.echo(f"~~~~ Compressing file '{fileorfolder}'...")
            upload_path = f"{fileorfolder}.gzip"    # Comp file name
            compress_file(fileorfolder, upload_path)
            click.echo(f"~~~~ Compression completed! Compressed file: \
                '{upload_path}")
            return upload_path


def compress_file(original: str, compressed: str) -> None:
    """Compresses file using gzip"""

    try:
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
                                                  "Access to Delivery Portal"
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


def file_type(fpath: str) -> str:
    """Guesses file mime based on extension"""

    if os.path.isdir(fpath):
        return "folder"
    else:
        kind = filetype.guess(fpath)    # Guess file type
        print("Kind : ", kind)
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


def project_access(user: str, project: str) -> bool:
    """Checks the users access to a specific project."""

    proj_couch = couch_connect()    # Connect to database
    user_projects = proj_couch['user_db'][user]['projects']

    # If the specified project is not present in the users project list
    # raise exception and quit
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

    # TODO -- currently not secure. Use scrypt or similar.

    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def validate_api_options(username, password, config, project):
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

    # Data to be uploaded entered? Exception raised if not.
    if not data and not pathfile:
        raise DeliveryPortalException("No data to be uploaded. "
                                      "Specify individual files/folders using "
                                      "the --data/-d option one or more times, "
                                      "or the --pathfile/-f. For help: "
                                      "'dp_api --help'")

    ### 1. Does the facility have >DP< access? ###
    click.echo("[*] Verifying Delivery Portal access...")
    access_granted, user_id = dp_access(username, password, upload)
    if not access_granted:
        raise DeliveryPortalException(
            "You are not authorized to access the Delivery Portal. Aborting.")
    else:
        click.echo("[**] Access granted!\n")

        ### 2. Does the facility have >project< access? ###
        ### 3. Does the project have S3 access (S3 delivery as option)? ###
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

            ### 4. Is the data compressed? ###
            for path in data:
                fname = path.split('/')[-1]      # Get file or folder name

                if os.path.isfile(path):    # <---- FILES
                    mime = file_type(path)  # Check mime type

                    if mime in compression_list():      # If file compressed format
                        # save current file name
                        upload_path[path] = path
                    else:                               # It not compressed format
                        ### 5. Perform compression ###
                        click.echo(f"~~~~ Compressing file '{path}'...")
                        upload_path[path] = f"{path}.gzip"
                        compress_file(path, upload_path[path])
                        click.echo(f"~~~~ Compression completed! Compressed file: \
                            '{upload_path[path]}")

                    ### 6. Generate file checksum. ###
                    click.echo("~~~~ Generating HMAC...")
                    hash_dict[path] = gen_hmac(upload_path[path]).hex()
                    click.echo("~~~~ HMAC generated!\n")

                elif os.path.isdir(path):   # <---- FOLDERS
                    ### 5. Perform compression ###
                    # If zip or tar --> files, not folders
                    click.echo(f"~~~~ Compressing directory '{path}'...")
                    try:
                        upload_path[path] = compress_folder(dir_path=path,
                                                            prev_path="")
                    except CompressionError as ce:
                        sys.exit(f"Could not compress folder {path}: {ce}")
                    else:
                        click.echo("~~~~ Compression completed!"
                                   f"Zip archive: '{upload_path[path]}'")

                    ### 6. Generate directory checksum. ###
                    click.echo("~~~~ Generating HMAC...")
                    hash_dict[path] = hash_dir(upload_path[path], key)
                    click.echo("~~~~ HMAC generated!\n")

                else:   # <---- TYPE UNKNOWN
                    sys.exit(f"Path type {path} not identified."
                             "Have you entered the correct path?")

                ### 7. Sensitive? ###
                if sensitive:
                    ### 8. Get user public key ###
                    cb_res = partial(
                        getpass, prompt="Passphrase for researcher private key ")
                    keys.generate(seckey=f"/Users/inaod568/Documents/keys/{fname}_researcher.sec",
                                  pubkey=f"/Users/inaod568/Documents/keys/{fname}researcher.pub", callback=cb_res)
                    res_pub = keys.get_public_key(
                        filepath=f"/Users/inaod568/Documents/keys/{fname}researcher.pub")
                    print("Researcher public key: ", res_pub)

                    ### 9. Generate facility keys ###
                    cb_fac = partial(
                        getpass, prompt="Passphrase for facility private key ")
                    keys.generate(seckey=f"/Users/inaod568/Documents/keys/{fname}_facility.sec",
                                  pubkey=f"/Users/inaod568/Documents/keys/{fname}facility.pub", callback=cb_fac)

                    ### 10. Encrypt data ###
                    # Get facility private key
                    fac_sec = keys.get_private_key(
                        filepath=f"/Users/inaod568/Documents/keys/{fname}_facility.sec", callback=cb_fac)
                    print("Facility private key : ", fac_sec)

                    # Encrypt
                    engine.encrypt(keys=[(0, fac_sec), (0, res_pub)], infile=upload_path[path], outfile=f"{upload_path[path]}.c4gh")

                    ### 11. Generate checksum ###
                    ### 12. Upload to sensitive bucket ###

            sys.exit()
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
