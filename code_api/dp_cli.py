"""

"""

# IMPORTS ############################################################ IMPORTS #

import click
import couchdb
import sys

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
    
    couch = couchdb.Server(f'http://localhost:5984')
    couch.login('delport', 'delport')
    return couch


def create_file_dict(files: tuple, sensitive: str) -> dict:
    """Creates dictionary containing information about file sensitivity"""

    sens_dict = dict()      # Dictionary for sensitive files
    nonsens_dict = dict()   # Dictionary for non-sensitive files

    if sensitive=="ALL":
        sens_dict = dict.fromkeys(files, True)
    elif sensitive=="NONE":
        nonsens_dict = dict.fromkeys(files, False)
    else: 
        for f_ in files: 
            if click.confirm(f"File: {f_} \t Sensitive?"):
                sens_dict[f_] = True
            else: 
                nonsens_dict[f_] = False

    return sens_dict, nonsens_dict


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
    password = click.prompt("Password\t", hide_input=True, confirmation_prompt=True)

    # Checks user access to DP
    access_granted = check_dp_access(username, password)
    if not access_granted: 
        sys.exit("You are not authorized to access the Delivery Portal. Aborting.")
    else: 
        # If project not chosen, ask for project to upload to
        # Check project access
        if not project: 
            project = click.prompt("Project to upload files to")
        
        project_access = check_project_access(username, project)    
        if not project_access: 
            sys.exit("Project access denied. Cancelling upload.") 
        else: 
                    
            # If not all sensitive/non-sensitive ask per file 
            # Save all sensitive in one dict and all non-sensitive in one
            sensi, non_sensi = create_file_dict(file, sensitive)
            
            # TODO: Create file checksum 
            # TODO: Save checksum in db
            # TODO: Encrypt files (ignoring the key stuff atm) + stream to s3 (if possible)
            # TODO: Compress files
            # TODO: Show success message
            # TODO: Save metadata to db
            # TODO: Show success message
            # TODO: Generate email to user of interest
