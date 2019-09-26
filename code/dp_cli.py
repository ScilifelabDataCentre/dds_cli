""""""

import click

@click.command()
@click.option('--file', '-f', multiple=True, help='File to upload. Eg: "-file /path/to/file/filetoupload.xxx". Don\'t forget the If multiple files, use option multiple times.')

def upload_files(file):
    """
    Main function. Handles the file upload.
    
    Parameters
    ----------
    file : str, optional
        

    Returns
    -------
  
    """
    click.echo(type(file))
    for f_ in file:
        click.echo(f_)


    