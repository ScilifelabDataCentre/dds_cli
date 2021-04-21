"""CLI for the Data Delivery System."""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import logging
import pathlib
import os
import concurrent.futures
import itertools
import sys

# Installed
import click
import rich
from rich.progress import Progress, BarColumn
from rich import pretty
import rich.console
import rich.prompt
import click_pathlib

# Own modules
import cli_code
from cli_code import directory
from cli_code import timestamp
from cli_code import data_putter as dp
from cli_code import data_lister as dl
from cli_code import data_remover as dr
from cli_code import data_getter as dg

###############################################################################
# START LOGGING CONFIG ################################# START LOGGING CONFIG #
###############################################################################

LOG = None

###############################################################################
# RICH CONFIG ################################################### RICH CONFIG #
###############################################################################

pretty.install()
console = rich.console.Console()

###############################################################################
# MAIN ################################################################# MAIN #
###############################################################################


@click.group()
@click.option("--debug", default=False, is_flag=True)
@click.pass_context
def cli(ctx, debug):
    """Main CLI command, sets up DDS info."""

    # Timestamp
    t_s = timestamp.TimeStamp().timestamp

    # Get user defined file destination if any specified
    dest_index = None
    if "--destination" in sys.argv:
        dest_index = sys.argv.index("--destination")
    elif "-d" in sys.argv:
        dest_index = sys.argv.index("-d")
    destination = (
        pathlib.Path(sys.argv[dest_index + 1])
        if dest_index is not None
        else pathlib.Path.cwd() / pathlib.Path(f"DataDelivery_{t_s}")
    )

    # Define alldirectories in DDS folder
    all_dirs = directory.DDSDirectory(
        path=destination, add_file_dir=any([x in sys.argv for x in ["put", "get"]])
    ).directories

    # Path to log file
    logfile = str(all_dirs["LOGS"] / pathlib.Path("ds.log"))

    # Create logger
    _ = cli_code.setup_custom_logger(filename=logfile, debug=debug)

    # Create logger
    global LOG
    LOG = logging.getLogger(__name__)
    LOG.setLevel(logging.DEBUG if debug else logging.WARNING)
    LOG.info("Logging started.")
    LOG.debug(destination)
    # Create context object
    ctx.obj = {
        "TIMESTAMP": t_s,
        "DDS_DIRS": all_dirs,
        "LOGFILE": logfile,
    }


###############################################################################
# PUT ################################################################### PUT #
###############################################################################


@cli.command()
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
        "Turn off progress bar for each individual file. Summary bars still visible."
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

    # Initialize delivery - check user access etc
    with dp.DataPutter(
        username=username,
        config=config,
        project=project,
        source=source,
        source_path_file=source_path_file,
        break_on_fail=break_on_fail,
        overwrite=overwrite,
        silent=silent,
        temporary_destination=dds_info["DDS_DIRS"],
    ) as putter:

        # Progress object to keep track of progress tasks
        with Progress(
            "{task.description}",
            BarColumn(bar_width=None),
            " • ",
            "[progress.percentage]{task.percentage:>3.1f}%",
            refresh_per_second=2,
        ) as progress:

            # Keep track of futures
            upload_threads = {}

            # Iterator to keep track of which files have been handled
            iterator = iter(putter.filehandler.data.copy())

            with concurrent.futures.ThreadPoolExecutor() as texec:
                # Start main progress bar - total uploaded files
                upload_task = progress.add_task(
                    description="Upload",
                    total=len(putter.filehandler.data),
                )

                # Schedule the first num_threads futures for upload
                for file in itertools.islice(iterator, num_threads):
                    LOG.info("Starting: %s", file)
                    upload_threads[
                        texec.submit(
                            putter.protect_and_upload,
                            file=file,
                            progress=progress,
                        )
                    ] = file

                try:
                    # Continue until all files are done
                    while upload_threads:
                        # Wait for the next future to complete, _ are the unfinished
                        done, _ = concurrent.futures.wait(
                            upload_threads,
                            return_when=concurrent.futures.FIRST_COMPLETED,
                        )

                        # Number of new upload tasks that can be started
                        new_tasks = 0

                        # Get result from future and schedule database update
                        for fut in done:
                            uploaded_file = upload_threads.pop(fut)
                            LOG.debug("Future done for file: %s", uploaded_file)

                            # Get result
                            try:
                                file_uploaded = fut.result()
                                LOG.info(
                                    "Upload of %s successful: %s",
                                    uploaded_file,
                                    file_uploaded,
                                )
                            except concurrent.futures.BrokenExecutor as err:
                                LOG.critical(
                                    "Upload of file %s failed! Error: %s",
                                    uploaded_file,
                                    err,
                                )
                                continue

                            # Increase the main progress bar
                            progress.advance(upload_task)

                            # New available threads
                            new_tasks += 1

                        # Schedule the next set of futures for upload
                        for next_file in itertools.islice(iterator, new_tasks):
                            LOG.info("Starting: %s", next_file)
                            upload_threads[
                                texec.submit(
                                    putter.protect_and_upload,
                                    file=next_file,
                                    progress=progress,
                                )
                            ] = next_file
                except KeyboardInterrupt:
                    LOG.warning(
                        "KeyboardInterrupt found - shutting down delivery gracefully. "
                        "This will finish the ongoing uploads. If you want to force "
                        "shutdown, repeat `Ctrl+C`. This is not advised. "
                    )

                    # Flag for threads to find
                    putter.stop_doing = True

                    # Stop and remove main progress bar
                    progress.remove_task(upload_task)

                    # Stop all tasks that are not currently uploading
                    _ = [
                        progress.stop_task(x)
                        for x in [
                            y.id
                            for y in progress.tasks
                            if y.fields.get("step") != "put"
                        ]
                    ]


###############################################################################
# LIST ################################################################# LIST #
###############################################################################


@cli.command()
@click.argument("proj_arg", required=False)
@click.argument("fold_arg", required=False)
@click.option("--project", "-p", required=False, help="Project ID.")
@click.option(
    "--folder",
    "-f",
    required=False,
    multiple=False,
    help="Folder to list files within.",
)
@click.option(
    "--size", "-sz", is_flag=True, default=False, help="Show size of project contents."
)
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
@click.pass_obj
def ls(_, proj_arg, fold_arg, project, folder, size, config, username):
    """List the projects and the files within the projects."""

    project = proj_arg if proj_arg is not None else project
    folder = fold_arg if fold_arg is not None else folder

    if project is None and size:
        console_ls = rich.console.Console(stderr=True, style="orange3")
        console_ls.print(
            "\nNB! Showing the project size is not implemented in the "
            "listing command at this time. No size will be displayed.\n"
        )

    with dl.DataLister(project=project, config=config, username=username) as lister:

        # List all projects if project is None and all files if project spec
        if lister.project is None:
            lister.list_projects()
        else:
            lister.list_files(folder=folder, show_size=size)


###############################################################################
# DELETE ############################################################# DELETE #
###############################################################################


@cli.command()
@click.argument("proj_arg", required=False)
@click.option("--project", required=False, type=str, help="Project ID.")
@click.option(
    "--username",
    "-u",
    required=False,
    type=str,
    help="Your Data Delivery System username.",
)
@click.option(
    "--config",
    "-c",
    required=False,
    type=click.Path(exists=True),
    help="Path to file with user credentials, destination, etc.",
)
@click.option(
    "--rm-all", "-a", is_flag=True, default=False, help="Remove all project contents."
)
@click.option(
    "--file",
    "-f",
    required=False,
    type=str,
    multiple=True,
    help="Path to file to remove.",
)
@click.option(
    "--folder",
    "-d",
    required=False,
    type=str,
    multiple=True,
    help="Path to folder to remove.",
)
@click.pass_obj
def rm(_, proj_arg, project, username, config, rm_all, file, folder):
    """Delete the files within a project."""

    # One of proj_arg or project is required
    if all(x is None for x in [proj_arg, project]):
        console.print("No project specified, cannot remove anything.")
        os._exit(os.EX_OK)

    # Either all or a file
    if rm_all and (file or folder):
        console.print(
            "The options '--rm-all' and '--file'/'--folder' " "cannot be used together."
        )
        os._exit(os.EX_OK)

    project = proj_arg if proj_arg is not None else project

    # Will not delete anything if no file or folder specified
    if project and not any([rm_all, file, folder]):
        console.print(
            "One of the options must be specified to perform "
            "data deletion: '--rm-all' / '--file' / '--folder'."
        )
        os._exit(os.EX_OK)

    # Warn if trying to remove all contents
    if rm_all:
        rm_all = (
            rich.prompt.Prompt.ask(
                "> Are you sure you want to delete all files within project "
                f"{project}?",
                choices=["y", "n"],
                default="n",
            )
            == "y"
        )

    with dr.DataRemover(project=project, username=username, config=config) as remover:

        if rm_all:
            remover.remove_all()

        if file:
            remover.remove_file(files=file)

        if folder:
            remover.remove_folder(folder=folder)


###############################################################################
# GET ################################################################### GET #
###############################################################################


@cli.command()
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
    type=click_pathlib.Path(
        exists=False, file_okay=False, dir_okay=True, resolve_path=True
    ),
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
        console.print(
            "\nFlag'--get-all' cannot be used together with options "
            "'--source'/'--source-path-fail'.\n"
        )
        os._exit(os.EX_OK)

    # Begin delivery
    with dg.DataGetter(
        username=username,
        config=config,
        project=project,
        get_all=get_all,
        source=source,
        source_path_file=source_path_file,
        break_on_fail=break_on_fail,
        destination=dds_info["DDS_DIRS"],
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
                    LOG.info("Starting: %s", file)
                    # Execute download
                    download_threads[
                        texec.submit(
                            getter.download_and_verify, file=file, progress=progress
                        )
                    ] = file

                while download_threads:
                    # Wait for the next future to complete
                    ddone, _ = concurrent.futures.wait(
                        download_threads, return_when=concurrent.futures.FIRST_COMPLETED
                    )

                    new_tasks = 0

                    for dfut in ddone:
                        downloaded_file = download_threads.pop(dfut)
                        LOG.info("Future done: %s", downloaded_file)

                        # Get result
                        try:
                            file_downloaded = dfut.result()
                            LOG.info(
                                "Download of %s successful: %s",
                                downloaded_file,
                                file_downloaded,
                            )
                        except concurrent.futures.BrokenExecutor as err:
                            LOG.critical(
                                "Download of file %s failed! Error: %s",
                                downloaded_file,
                                err,
                            )
                            continue

                        new_tasks += 1
                        progress.advance(task_dwnld)

                    # Schedule the next set of futures for download
                    for next_file in itertools.islice(iterator, new_tasks):
                        LOG.info("Starting: %s", next_file)
                        # Execute download
                        download_threads[
                            texec.submit(
                                getter.download_and_verify,
                                file=next_file,
                                progress=progress,
                            )
                        ] = next_file
