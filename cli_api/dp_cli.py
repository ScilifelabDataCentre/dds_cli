import click

@click.command()
@click.option('--file', '-f', multiple=True, help='File to upload. Eg: "-file /path/to/file/filetoupload.xxx". Don\'t forget the If multiple files, use option multiple times.')
def cli(file):
    """Example script."""
    click.echo('Hello World!')
    click.echo(file)