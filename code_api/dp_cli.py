"""

"""

# IMPORTS ############################################################ IMPORTS #

import click
import couchdb


# GLOBAL VARIABLES ########################################## GLOBAL VARIABLES #


# CLASSES ############################################################ CLASSES #


# FUNCTIONS ######################################################## FUNCTIONS #

def check_dp_access(username: str, password: str) -> bool:
    """Check existance of user in database."""

    couch = couch_connect()
    user_db = couch['dp_users']
    if not username in user_db:
        click.echo("This user does not have a Delivery Portal account. Contact xxx for more information.")
        return False
    elif user_db[username]['user']['password'] != password: 
        click.echo("The password is incorrect. Upload cancelled.")
        return False
    return True


def couch_connect():
    """Connect to a couchdb interface."""
    
    couch = couchdb.Server(f'http://localhost:5984')
    couch.login('delport', 'delport')
    return couch


def create_file_dict(files: tuple, sensitive: str) -> dict:
    """Creates dictionary containing information about file sensitivity"""

    file_dict = dict()
    if sensitive=="ALL":
        file_dict = dict.fromkeys(files, True)
    elif sensitive=="NONE":
        file_dict = dict.fromkeys(files, False)
    else: 
        for f_ in files: 
            file_dict[f_] = click.confirm(f"File: {f_} \t Sensitive?")

    return file_dict


# MAIN ################################################################## MAIN #

@click.command()
@click.option('--file', '-f', multiple=True, type=click.Path(exists=True), help='File to upload.')
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

    # Abort if no file entered on call
    if not file: 
        click.echo("No files were entered. Aborting...")
        click.Abort

    # Ask for DP username if not entered 
    # and associated password 
    if not username:  
        username = click.prompt("Enter username\t", type=str)
    password = click.prompt("Password\t", hide_input=True, confirmation_prompt=True)

    # Checks user access to DP
    access_granted = check_dp_access(username, password)
    if not access_granted:
        click.Abort 
    
    # TODO: Ask for project to upload to (if not entered)

    # TODO: Check user access to project

    # TODO: If not all sensitive/non-sensitive ask per file 
    click.echo(sensitive)
    files_sensitive = create_file_dict(file, sensitive)
    
    # TODO: Create file checksum 
    # TODO: Save checksum in db
    # TODO: Encrypt files (ignoring the key stuff atm) + stream to s3 (if possible)
    # TODO: Compress files
    # TODO: Show success message
    # TODO: Save metadata to db
    # TODO: Show success message
    # TODO: Generate email to user of interest
