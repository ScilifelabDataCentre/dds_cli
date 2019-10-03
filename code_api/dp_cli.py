"""

"""

# IMPORTS ############################################################ IMPORTS #

import click
import couchdb
import sys
import hashlib
import os
import filetype


# GLOBAL VARIABLES ########################################## GLOBAL VARIABLES #


# CLASSES ############################################################ CLASSES #


# FUNCTIONS ######################################################## FUNCTIONS #

def check_dp_access(username: str, password: str) -> bool:
    """Check existance of user in database and the password validity."""

    couch = couch_connect()
    user_db = couch['dp_users']
    if not username in user_db:
        sys.exit("This user does not have a Delivery Portal account. Contact xxx for more information.")
    elif user_db[username]['user']['password'] != password: 
        sys.exit("The password is incorrect. Upload cancelled.")
    return True


def check_project_access(username: str, project: str) -> bool:
    """Checks the users access to a specific project."""

    couch = couch_connect()
    user_db = couch['dp_users']

    if project not in user_db[username]['projects']:
        if click.confirm(f"You do not have access to the specified project '{project}'.\n \
            Change project?"):
            project = click.prompt("Project to upload files to")
            check_project_access(username, project) 
        else: 
            sys.exit("Project access denied. Aborting upload.")
    else: 
        return True


def couch_connect():
    """Connect to a couchdb interface."""
    
    couch = couchdb.Server('http://localhost:5984')
    couch.login('delport', 'delport')
    return couch


def create_file_dict(files: tuple, sensitive: str) -> dict:
    """Creates separate dictionaries for sensitive and non-sensitive files"""

    sens_dict = dict()      # Dictionary for sensitive files
    nonsens_dict = dict()   # Dictionary for non-sensitive files

    # If all files are sensitive or non-sensitive, save all filenames in same dict
    # Otherwise user input to determine
    if sensitive=="ALL": 
        sens_dict = dict.fromkeys(files, dict())
    elif sensitive=="NONE":
        nonsens_dict = dict.fromkeys(files, dict())
    else: 
        for f_ in files: 
            if click.confirm(f"File: {f_} \t Sensitive?"):
                sens_dict[f_] = dict()
            else: 
                nonsens_dict[f_] = dict()

    return sens_dict, nonsens_dict


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


def file_type(filename: str):
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


# MAIN ################################################################## MAIN #

@click.command()
@click.option('--file', '-f', required=True, multiple=True, type=click.Path(exists=True), help='File to upload.')
@click.option('--username', '-u', type=str, help="Delivery Portal username.")
@click.option('--project', '-p', type=str, help="Project to upload files to.")
@click.option('--sensitive', type=click.Choice(['ALL', 'NONE', 'MIXED'], case_sensitive=False), help="Sensitive or non-sensitive information.")
def upload_files(file: str, username: str, project: str, sensitive: str):
    """Main function. Handles file upload. 
    
    * If multiple files, use option multiple times.
    * File name cannot start with "-". 

    Example one file: 
        "--file /path/to/file.xxx" 
    Example multiple files: 
        "--file /path/to/file1.xxx --file /path/to/file2.xxx ..." etc.
    """

    # Ask for DP username if not entered 
    # and associated password 
    if not username:  
        username = click.prompt("Enter username\t", type=str)
    # password = click.prompt("Password\t", hide_input=True, confirmation_prompt=True)
    password = "facility1"  # development

    # Checks user access to DP
    access_granted = check_dp_access(username, password)
    if not access_granted: 
        sys.exit("You are not authorized to access the Delivery Portal. Aborting.")
    else: 
        # If project not chosen, ask for project to upload to
        # Check project access
        if not project: 
            # project = click.prompt("Project to upload files to")
            project = "0549ccc37f19cf10f62ae436f30038e4"    # development

        project_access = check_project_access(username, project)    
        if not project_access: 
            sys.exit("Project access denied. Cancelling upload.") 
        else: 
            # If not all sensitive/non-sensitive ask per file 
            # Save all sensitive in one dict and all non-sensitive in one
            sensi, non_sensi = create_file_dict(file, sensitive)
            
            # Create file checksums
            for s_ in sensi: 
                sensi[s_]['checksum'] = gen_sha512(s_)  # Save checksum
                sensi[s_]['size'] = get_filesize(s_)    # Save file size
                sensi[s_]['format'] = file_type(s_)
                click.echo(sensi)

            for ns_ in non_sensi:
                non_sensi[ns_]['checksum'] = gen_sha512(ns_)    # Save checksum
                non_sensi[ns_]['size'] = get_filesize(ns_)      # Save file size
                non_sensi[ns_]['format'] = file_type(ns_)
            # TODO: Save checksum in db


            # TODO: Encrypt files (ignoring the key stuff atm) + stream to s3 (if possible)
            # TODO: Compress files
            # TODO: Show success message
            # TODO: Save metadata to db
            # TODO: Show success message
            # TODO: Generate email to user of interest
