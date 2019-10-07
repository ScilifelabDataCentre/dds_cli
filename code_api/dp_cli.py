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


# GLOBAL VARIABLES ########################################## GLOBAL VARIABLES #


# CLASSES ############################################################ CLASSES #

class CouchDBException(Exception):
    """Custom exception class. Handles errors in database operations."""

    def __init__(self, msg: str):
        """Passes message from exception call to the base class __init__."""

        super().__init__(msg)


# FUNCTIONS ######################################################## FUNCTIONS #

def check_dp_access(username: str, password: str) -> bool:
    """Check existance of user in database and the password validity."""

    dp_couch, dp_token = couch_connect()
    user_db = dp_couch['dp_users']
    if not username in user_db:
        sys.exit("This user does not have a Delivery Portal account. "
                 "Contact xxx for more information.")
    elif user_db[username]['user']['password'] != password:
        sys.exit("The password is incorrect. Upload cancelled.")
    
    couch_disconnect(dp_couch, dp_token)
    return True


def check_project_access(username: str, project: str) -> bool:
    """Checks the users access to a specific project."""

    proj_couch, proj_token = couch_connect()
    user_db = proj_couch['dp_users']

    if project not in user_db[username]['projects']:
        if click.confirm("You do not have access to the specified project" +
                         f"'{project}'.\n Change project?"):
            project = click.prompt("Project to upload files to")
            check_project_access(username, project)
        else:
            sys.exit("Project access denied. Aborting upload.")
    
    couch_disconnect(proj_couch, proj_token)
    return True


def couch_connect():
    """Connect to a couchdb interface."""

    try: 
        couch = couchdb.Server('http://localhost:5984')
        token = couch.login('delport', 'delport')
    except CouchDBException:
        print("Database login failed.")

    return couch, token


def couch_disconnect(couch, token):
    """Disconnect from couchdb interface."""

    try: 
        couch.logout(token)
    except CouchDBException:
        print("Could not logout from database.")


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


def file_type(filename: str) -> str:
    """Guesses file type based on extension"""

    type_ = filetype.guess(filename)
    if type_ is None:
        try:
            extension = os.path.splitext(filename)[1]
        except:
            sys.stderr.write("Your file doesn't have an extension.")

        if extension in (".txt"):
            type_ = "text"
        elif extension in (".csv"):
            type_ = "csv"
        elif extension in (".abi", ".ab1"):
            type_ = "abi"
        elif extension in (".embl"):
            type_ = "embl"
        elif extension in (".clust", ".cw", ".clustal"):
            type_ = "clustal"
        elif extension in (".fa", ".fasta", ".fas", ".fna", ".faa", ".afasta"):
            type_ = "fasta"
        elif extension in (".fastq", ".fq"):
            type_ = "fastq"
        elif extension in (".gbk", ".genbank", ".gb"):
            type_ = "genbank"
        elif extension in (".paup", ".nexus"):
            type_ = "nexus"
        else:
            click.echo("Could not determine file format.")

    return type_


# def split_files():

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

    file = ("testfile1.fna", "testfile2.fna", "testfile3.fna",
            "testfile4.fna",)  # TODO: remove after dev

    sensitive = True

    # Ask for DP username if not entered
    # and associated password
    if not username:
        username = click.prompt("Enter username\t", type=str)
    # password = click.prompt("Password\t", hide_input=True, confirmation_prompt=True)
    password = "facility1"  # TODO: Change after development

    # Checks user access to DP
    access_granted = check_dp_access(username, password)
    if not access_granted:
        sys.exit("You are not authorized to access the Delivery Portal. Aborting.")
    else:
        # If project not chosen, ask for project to upload to
        # Check project access
        if not project:
            # project = click.prompt("Project to upload files to")
            # TODO: Change after development
            project = "0549ccc37f19cf10f62ae436f30038e4"

        project_access = check_project_access(username, project)
        if not project_access:
            sys.exit("Project access denied. Cancelling upload.")
        else:
            # Create file checksums and save in database
            # Save checksum and metadata in db
            couch, token = couch_connect()             # Connect to database
            project_db = couch['projects']      # Get project database

            if project not in project_db:       # Check if project exists in database
                sys.exit(
                    "The specified project is not recorded in the database. Aborting upload.")
            else:                                       # If project exists
                project_doc = project_db[project]       # Get project document
                project_files = project_doc['files']    # Get files

                # Get project sensitive information from database
                if 'project_info' in project_doc and 'sensitive' in project_doc['project_info']:
                    sensitive = project_db[project]['project_info']['sensitive']

                for f_ in file:    # Generate and save checksums
                    try:
                        project_files[f_] = {"checksum": gen_sha512(f_),
                                             "format": file_type(f_),
                                             "size": get_filesize(f_),
                                             "date_uploaded": get_current_time()}   # Save checksum in db
                    except CouchDBException:
                        print(
                            f"Could not update file {f_} metadata.")

                try:
                    project_db.save(project_doc)
                except CouchDBException:
                    print(
                        f"Updating project {project} failed. Cancelling upload.")

                couch_disconnect(couch, token)     # Logout from couchdb
            
                if sensitive: 
                    click.echo("start encryption...")
                    
                    
            # TODO: Encrypt files (ignoring the key stuff atm) + stream to s3 (if possible)
            # TODO: Compress files
            # TODO: Show success message
            # TODO: Delete from database if failed upload
            # TODO: Save metadata to db
            # TODO: Show success message
            # TODO: Generate email to user of interest
