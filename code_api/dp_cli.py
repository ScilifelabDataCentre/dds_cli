import click

@click.command()
@click.option('--file', '-f', multiple=True, type=click.Path(exists=True), help='File to upload.')
def upload_files(file: str):
    """Main function. Handles file upload. 
    
    * If multiple files, use option multiple times.
    * File name cannot start with "-". 

    Example one file: 
        "--file /path/to/file.xxx" 
    Example multiple files: 
        "--file /path/to/file1.xxx --file /path/to/file2.xxx ..." etc.
    """

    if not file: 
        if click.confirm("No files were entered, would you like to add files? \t "):
            file += click.prompt("Enter files (minimum one)\t ", type=tuple)
        else: 
            click.echo("No files were entered. Aborting...")
            click.Abort


    click.echo(file)
    for f_ in file: 
        click.echo(f_)
        click.echo(click.format_filename(f_))
    