"""CLI for the Data Delivery System."""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import concurrent.futures
import itertools
import logging
import os
import pathlib
import sys
from logging.config import dictConfig

# Installed
import click
import click_pathlib
import rich
import rich.console
import rich.logging
import rich.prompt
from rich import pretty
from rich.progress import Progress, BarColumn

# Own modules
import dds_cli
import dds_cli.exceptions
import dds_cli.data_getter
import dds_cli.data_lister
import dds_cli.data_putter
import dds_cli.data_remover
import dds_cli.directory
import dds_cli.timestamp

###############################################################################
# START LOGGING CONFIG ################################# START LOGGING CONFIG #
###############################################################################

LOG = logging.getLogger()

###############################################################################
# MAIN ################################################################# MAIN #
###############################################################################


# Print header to STDERR
stderr = rich.console.Console(stderr=True)
stderr.print(
    "\n\n[green]     ︵",
    "\n[green] ︵ (  )   ︵",
    "\n[green](  ) ) (  (  )[/]   [bold]SciLifeLab Data Delivery System",
    "\n[green] ︶  (  ) ) ([/]    [blue][link={0}]{0}[/link]".format(dds_cli.__url__),
    f"\n[green]      ︶ (  )[/]    [dim]Version {dds_cli.__version__}",
    "\n[green]          ︶\n",
    highlight=False,
)


@click.group()
@click.option(
    "-v", "--verbose", is_flag=True, default=False, help="Print verbose output to the console."
)
@click.option("-l", "--log-file", help="Save a verbose log to a file.", metavar="<filename>")
@click.version_option(version=dds_cli.__version__, prog_name=dds_cli.__title__)
@click.pass_context
def dds_main(ctx, verbose, log_file):
    """Main CLI command, sets up DDS info."""

    # Set the base logger to output DEBUG
    LOG.setLevel(logging.DEBUG)

    # Set up logs to the console
    LOG.addHandler(
        rich.logging.RichHandler(
            level=logging.DEBUG if verbose else logging.INFO,
            console=rich.console.Console(stderr=True),
            show_time=False,
            markup=True,
        )
    )

    # Set up logs to a file if we asked for one
    if log_file:
        log_fh = logging.FileHandler(log_file, encoding="utf-8")
        log_fh.setLevel(logging.DEBUG)
        log_fh.setFormatter(
            logging.Formatter("[%(asctime)s] %(name)-20s [%(levelname)-7s]  %(message)s")
        )
        LOG.addHandler(log_fh)

    # Check that the config file exists
    config_file = None
    if "--help" not in sys.argv:
        if not any([x in sys.argv for x in ["--config", "-c", "--username", "-u"]]):
            config_file = pathlib.Path().home() / pathlib.Path(".dds-cli.json")
            if not config_file.is_file():
                LOG.error("Could not find the config file '.dds-cli.json'")
                os._exit(1)

    # Create context object
    ctx.obj = {
        "CONFIG": config_file,
    }


###############################################################################
# PUT ################################################################### PUT #
###############################################################################


@dds_main.command()
@click.option(
    "--config",
    "-c",
    required=False,
    type=click.Path(exists=True),
    help="Path to file with user credentials, destination, etc.",
)
@click.option(
    "--username",
    "-u",
    required=False,
    type=str,
    help="Your Data Delivery System username",
)
@click.option(
    "--project",
    "-p",
    required=False,
    type=str,
    help="Project ID to which you're uploading data",
)
@click.option(
    "--source",
    "-s",
    required=False,
    type=click.Path(exists=True),
    multiple=True,
    help="Path to file or directory (local)",
)
@click.option(
    "--source-path-file",
    "-spf",
    required=False,
    type=click.Path(exists=True),
    multiple=False,
    help="File containing path to files or directories",
)
@click.option(
    "--break-on-fail",
    is_flag=True,
    default=False,
    show_default=True,
    help="Cancel upload of all files if one fails",
)
@click.option(
    "--overwrite",
    is_flag=True,
    default=False,
    show_default=True,
    help="Overwrite files if already uploaded",
)
@click.option(
    "--num-threads",
    "-nt",
    required=False,
    multiple=False,
    default=4,
    show_default=True,
    type=click.IntRange(1, 32),
    help="Number of parallel threads to perform the delivery",
)
@click.option(
    "--silent",
    is_flag=True,
    default=False,
    show_default=True,
    help=(
        "Turn off progress bar for each individual file. Summary bars still visible. "
        "Suggested for uploads including a large number of files."
    ),
)
@click.pass_obj
def put(
    dds_info,
    config,
    username,
    project,
    source,
    source_path_file,
    break_on_fail,
    overwrite,
    num_threads,
    silent,
):
    """Processes and uploads specified files to the cloud."""
    try:
        dds_cli.data_putter.put(
            dds_info,
            dds_info["CONFIG"] if config is None else config,
            username,
            project,
            source,
            source_path_file,
            break_on_fail,
            overwrite,
            num_threads,
            silent,
        )
    except (dds_cli.exceptions.AuthenticationError, dds_cli.exceptions.UploadError) as e:
        LOG.error(e)
        sys.exit(1)


###############################################################################
# LIST ################################################################# LIST #
###############################################################################


@dds_main.command()
@click.argument("fold_arg", required=False)  # Needs to be before proj_arg
@click.argument("proj_arg", required=False)
@click.option("--project", "-p", required=False, help="Project ID.")
@click.option("--projects", "-lp", is_flag=True, help="List all project connected to your account.")
@click.option(
    "--folder", "-fl", required=False, multiple=False, help="Folder to list files within."
)
@click.option("--size", "-sz", is_flag=True, default=False, help="Show size of project contents.")
@click.option(
    "--username", "-u", required=False, type=str, help="Your Data Delivery System username."
)
@click.option(
    "--config",
    "-c",
    required=False,
    type=click.Path(exists=True),
    help="Path to file with user credentials, destination, etc.",
)
@click.pass_obj
def ls(dds_info, proj_arg, fold_arg, project, projects, folder, size, username, config):
    """List the projects and the files within the projects."""

    project = proj_arg if proj_arg is not None else project
    folder = fold_arg if fold_arg is not None else folder

    if projects and size:
        LOG.warning("NB! Listing the project size is not yet implemented.")

    try:
        with dds_cli.data_lister.DataLister(
            project=project,
            project_level=projects,
            config=dds_info["CONFIG"] if config is None else config,
            username=username,
        ) as lister:
            # List all projects if project is None and all files if project spec
            if lister.project is None:
                lister.list_projects()
            else:
                lister.list_files(folder=folder, show_size=size)
    except (dds_cli.exceptions.NoDataError) as e:
        LOG.warning(e)
        sys.exit(0)
    except (dds_cli.exceptions.APIError, dds_cli.exceptions.AuthenticationError) as e:
        LOG.error(e)
        sys.exit(1)


###############################################################################
# DELETE ############################################################# DELETE #
###############################################################################


@dds_main.command()
@click.argument("proj_arg", required=False)
@click.option("--project", required=False, type=str, help="Project ID.")
@click.option(
    "--username", "-u", required=False, type=str, help="Your Data Delivery System username."
)
@click.option("--rm-all", "-a", is_flag=True, default=False, help="Remove all project contents.")
@click.option(
    "--file", "-f", required=False, type=str, multiple=True, help="Path to file to remove."
)
@click.option(
    "--folder", "-fl", required=False, type=str, multiple=True, help="Path to folder to remove."
)
@click.option(
    "--config",
    "-c",
    required=False,
    type=click.Path(exists=True),
    help="Path to file with user credentials, destination, etc.",
)
@click.pass_obj
def rm(dds_info, proj_arg, project, username, rm_all, file, folder, config):
    """Delete the files within a project."""

    # One of proj_arg or project is required
    if all(x is None for x in [proj_arg, project]):
        LOG.error("No project specified, cannot remove anything.")
        os._exit(1)

    # Either all or a file
    if rm_all and (file or folder):
        LOG.error("The options '--rm-all' and '--file'/'--folder' cannot be used together.")
        os._exit(1)

    project = proj_arg if proj_arg is not None else project

    # Will not delete anything if no file or folder specified
    if project and not any([rm_all, file, folder]):
        LOG.error(
            "One of the options must be specified to perform data deletion: '--rm-all' / '--file' / '--folder'."
        )
        os._exit(1)

    # Warn if trying to remove all contents
    if rm_all:
        if not rich.prompt.Confirm.ask(
            f"Are you sure you want to delete all files within project '{project}'?"
        ):
            LOG.info("Probably for the best. Exiting.")
            os._exit(0)

    with dds_cli.data_remover.DataRemover(
        project=project,
        username=username,
        config=dds_info["CONFIG"] if config is None else config,
    ) as remover:

        if rm_all:
            remover.remove_all()

        if file:
            remover.remove_file(files=file)

        if folder:
            remover.remove_folder(folder=folder)


###############################################################################
# GET ################################################################### GET #
###############################################################################


@dds_main.command()
@click.option(
    "--config",
    "-c",
    required=False,
    type=click.Path(exists=True),
    help="Path to file with user credentials, destination, etc.",
)
@click.option(
    "--username",
    "-u",
    required=False,
    type=str,
    help="Your Data Delivery System username.",
)
@click.option(
    "--project",
    "-p",
    required=False,
    type=str,
    help="Project ID to which you're uploading data.",
)
@click.option(
    "--get-all",
    "-a",
    is_flag=True,
    default=False,
    show_default=True,
    help="Download all project contents.",
)
@click.option(
    "--source",
    "-s",
    required=False,
    type=str,
    multiple=True,
    help="Path to file or directory (local).",
)
@click.option(
    "--source-path-file",
    "-spf",
    required=False,
    type=click.Path(exists=True),
    multiple=False,
    help="File containing path to files or directories. ",
)
@click.option(
    "--destination",
    "-d",
    required=False,
    type=click_pathlib.Path(exists=False, file_okay=False, dir_okay=True, resolve_path=True),
    multiple=False,
    help="Destination of downloaded files.",
)
@click.option(
    "--break-on-fail",
    is_flag=True,
    default=False,
    show_default=True,
    help="Cancel download of all files if one fails",
)
@click.option(
    "--num-threads",
    "-nt",
    required=False,
    multiple=False,
    default=4,
    show_default=True,
    type=click.IntRange(1, 32),
    help="Number of parallel threads to perform the download.",
)
@click.option(
    "--silent",
    is_flag=True,
    default=False,
    show_default=True,
    help="Turn off progress bar for each individual file. Summary bars still visible.",
)
@click.option(
    "--verify-checksum",
    is_flag=True,
    default=False,
    show_default=True,
    help="Perform SHA-256 checksum verification after download (slower).",
)
@click.pass_obj
def get(
    dds_info,
    config,
    username,
    project,
    get_all,
    source,
    source_path_file,
    destination,
    break_on_fail,
    num_threads,
    silent,
    verify_checksum,
):
    """Downloads specified files from the cloud and restores the original format."""

    if get_all and (source or source_path_file):
        LOG.error(
            "Flag '--get-all' cannot be used together with options '--source'/'--source-path-fail'."
        )
        os._exit(1)

    # Begin delivery
    with dds_cli.data_getter.DataGetter(
        username=username,
        config=dds_info["CONFIG"] if config is None else config,
        project=project,
        get_all=get_all,
        source=source,
        source_path_file=source_path_file,
        break_on_fail=break_on_fail,
        destination=destination,
        silent=silent,
        verify_checksum=verify_checksum,
    ) as getter:

        with Progress(
            "{task.description}",
            BarColumn(bar_width=None),
            " • ",
            "[progress.percentage]{task.percentage:>3.1f}%",
            refresh_per_second=2,
        ) as progress:

            # Keep track of futures
            download_threads = {}

            # Iterator to keep track of which files have been handled
            iterator = iter(getter.filehandler.data.copy())

            with concurrent.futures.ThreadPoolExecutor() as texec:
                task_dwnld = progress.add_task(
                    "Download", total=len(getter.filehandler.data), step="summary"
                )

                # Schedule the first num_threads futures for upload
                for file in itertools.islice(iterator, num_threads):
                    LOG.info(f"Starting: {file}")
                    # Execute download
                    download_threads[
                        texec.submit(getter.download_and_verify, file=file, progress=progress)
                    ] = file

                while download_threads:
                    # Wait for the next future to complete
                    ddone, _ = concurrent.futures.wait(
                        download_threads, return_when=concurrent.futures.FIRST_COMPLETED
                    )

                    new_tasks = 0

                    for dfut in ddone:
                        downloaded_file = download_threads.pop(dfut)
                        LOG.info(
                            f"Future done: {downloaded_file}",
                        )

                        # Get result
                        try:
                            file_downloaded = dfut.result()
                            LOG.info(f"Download of {downloaded_file} successful: {file_downloaded}")
                        except concurrent.futures.BrokenExecutor as err:
                            LOG.critical(f"Download of file {downloaded_file} failed! Error: {err}")
                            continue

                        new_tasks += 1
                        progress.advance(task_dwnld)

                    # Schedule the next set of futures for download
                    for next_file in itertools.islice(iterator, new_tasks):
                        LOG.info(f"Starting: {next_file}")
                        # Execute download
                        download_threads[
                            texec.submit(
                                getter.download_and_verify,
                                file=next_file,
                                progress=progress,
                            )
                        ] = next_file
