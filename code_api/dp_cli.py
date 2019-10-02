"""

"""

import click

class S3key(click.ParamType):

    def convert(self, value, param, ctx):
        return value

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

    # Print tuple with entered files and each separate file in tuple
    click.echo(file)
    for f_ in file: 
        click.echo(click.format_filename(f_))

    # Ask for DP username if not entered 
    # and associated password 
    if not username:  
        username = click.prompt("Enter username\t", type=str)
    password = click.prompt("Password\t", hide_input=True, confirmation_prompt=True)

    # TODO: Check user access to DP
    
    # TODO: Ask for project to upload to (if not entered)

    # TODO: Check user access to project

    # TODO: If not all sensitive/non-sensitive ask per file 
    click.echo(sensitive)
    files_sensitive = dict()
    if sensitive=="ALL":
        for f_ in file: 
            files_sensitive[f_] = True
    elif sensitive=="NONE":
        for f_ in file: 
            files_sensitive[f_] = False
    else: 
        for f_ in file: 
            files_sensitive[f_] = click.confirm(f"File: {f_} \t Sensitive?")

# TODO: 7. Create checksum + save in db
# TODO: 8. Encrypt files (ignoring the key stuff atm) + stream to s3 (if possible)
# TODO: (8b. Compress files) 
# TODO: 9. Show success message
# TODO: 10. Save metadata to db
# TODO: 11. Show success message
# TODO: 12. Generate email to user of interest
