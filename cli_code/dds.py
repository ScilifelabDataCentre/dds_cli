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

# Installed
import click
import rich
from rich import pretty
import rich.console
import rich.prompt

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

    # Path to new directory
    dds_dir = pathlib.Path.cwd() / pathlib.Path(f"DataDelivery_{t_s}")

    # Define alldirectories in DDS folder
    all_dirs = directory.DDSDirectory(path=dds_dir).directories

    # Path to log file
    logfile = str(all_dirs["LOGS"] / pathlib.Path("ds.log"))

    # Create logger
    cli_code.setup_custom_logger(filename=logfile, debug=debug)

    global LOG
    LOG = logging.getLogger(__name__)
    LOG.setLevel(logging.DEBUG if debug else logging.WARNING)

    # Create context object
    ctx.obj = {
        "TIMESTAMP": t_s,
        "DDS_DIRS": all_dirs,
        "LOGFILE": logfile,
        # "LOGGER": LOG
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
    default=min(32, os.cpu_count() + 4),
    show_default=True,
    type=click.IntRange(1, 32),
    help="Number of parallel threads to perform the delivery",
)
@click.pass_obj
def put(
    _,
    config,
    username,
    project,
    source,
    source_path_file,
    break_on_fail,
    overwrite,
    num_threads,
):
    """Processes and uploads specified files to the cloud."""

    # Begin delivery
    with dp.DataPutter(
        username=username,
        config=config,
        project=project,
        source=source,
        source_path_file=source_path_file,
        break_on_fail=break_on_fail,
        overwrite=overwrite,
    ) as putter:

        # Keep track of futures
        upload_threads = {}  # Upload related
        db_threads = {}  # Database related

        # Iterator to keep track of which files have been handled
        iterator = iter(putter.filehandler.data.copy())

        with concurrent.futures.ThreadPoolExecutor() as texec:

            # Schedule the first num_threads futures for upload
            for file in itertools.islice(iterator, num_threads):
                LOG.debug("Uploading file %s...", file)
                upload_threads[texec.submit(putter.put, file=file)] = file

            # Continue until all files are done
            while upload_threads:
                # Wait for the next future to complete
                udone, _ = concurrent.futures.wait(
                    upload_threads, return_when=concurrent.futures.FIRST_COMPLETED
                )

                # Get result from future and schedule database update
                for ufut in udone:
                    uploaded_file = upload_threads.pop(ufut)
                    LOG.debug("...File %s uploaded!", uploaded_file)

                    # Get result
                    try:
                        _ = ufut.result()
                    except concurrent.futures.BrokenExecutor as err:
                        LOG.critical(
                            "Upload of file %s failed! Error: %s", uploaded_file, err
                        )
                        continue

                    # Schedule file for db update
                    LOG.debug("Adding to db: %s...", uploaded_file)
                    db_threads[
                        texec.submit(putter.add_file_db, file=uploaded_file)
                    ] = uploaded_file

                new_tasks = 0

                # Continue until all files are done
                while db_threads:
                    # Wait for the next future to complete
                    done_db, _ = concurrent.futures.wait(
                        db_threads, return_when=concurrent.futures.FIRST_COMPLETED
                    )

                    # Get result from future
                    for fut_db in done_db:
                        added_file = db_threads.pop(fut_db)
                        LOG.debug("...File added to db: %s", added_file)

                        new_tasks += 1

                        # Get result
                        try:
                            _ = fut_db.result()
                        except concurrent.futures.BrokenExecutor as err:
                            LOG.critical(
                                "Adding of file %s to database failed! Error: %s",
                                uploaded_file,
                                err,
                            )
                            continue

                # Schedule the next set of futures for upload
                for ufile in itertools.islice(iterator, len(done_db)):
                    LOG.debug("Uploading file %s...", ufile)
                    upload_threads[texec.submit(putter.put, file=ufile)] = ufile


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
    help="Path within bucket to file to remove.",
)
@click.option(
    "--folder",
    "-d",
    required=False,
    type=str,
    multiple=True,
    help="Path within bucket to folder to remove.",
)
@click.pass_obj
def rm(_, proj_arg, project, username, config, rm_all, file, folder):
    """Delete the files within a project."""

    # One of proj_arg or project is required
    if all(x is None for x in [proj_arg, project]):
        global console
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
            console_rm = rich.console.Console(stderr=True, style="orange3")
            console_rm.print(f"\nRemoving all files in project {project}...\n")

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
    default=min(32, os.cpu_count() + 4),
    show_default=True,
    type=click.IntRange(1, 32),
    help="Number of parallel threads to perform the download.",
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
    break_on_fail,
    num_threads,
):

    if get_all and (source or source_path_file):
        console.print(
            "\nFlag'--get-all' cannot be used together with options "
            "'--source'/'--source-path-fail'.\n"
        )
        os._exit(os.EX_OK)

    with dg.DataGetter(
        username=username,
        config=config,
        project=project,
        get_all=get_all,
        source=source,
        source_path_file=source_path_file,
        break_on_fail=break_on_fail,
        destination=dds_info["DDS_DIRS"]["FILES"],
    ) as getter:

        # Keep track of futures
        download_threads = {}
        db_threads = {}

        # Iterator to keep track of which files have been handled
        iterator = iter(getter.filehandler.data.copy())

        with concurrent.futures.ThreadPoolExecutor() as texec:

            # Schedule the first num_threads futures for upload
            for file in itertools.islice(iterator, num_threads):
                LOG.debug("Downloading file %s...", file)
                download_threads[texec.submit(getter.get, file=file)] = file

            while download_threads:
                # Wait for the next future to complete
                ddone, _ = concurrent.futures.wait(
                    download_threads, return_when=concurrent.futures.FIRST_COMPLETED
                )

                for dfut in ddone:
                    downloaded_file = download_threads.pop(dfut)
                    LOG.debug("...File %s downloaded!", downloaded_file)

                    # Get result
                    try:
                        _ = dfut.result()
                    except concurrent.futures.BrokenExecutor as err:
                        LOG.critical(
                            "Download of file %s failed! Error: %s",
                            downloaded_file,
                            err,
                        )
                        continue

                    # Schedule file for db update
                    LOG.debug("Updating db info for file %s...", downloaded_file)
                    db_threads[
                        texec.submit(getter.update_db, file=downloaded_file)
                    ] = downloaded_file

                new_tasks = 0

                # Continue until all files are done
                while db_threads:
                    # Wait for the next future to complete
                    done_db, _ = concurrent.futures.wait(
                        db_threads, return_when=concurrent.futures.FIRST_COMPLETED
                    )

                    # Get result from future
                    for fut_db in done_db:
                        updated_file = db_threads.pop(fut_db)
                        LOG.debug("...File updated: %s", updated_file)

                        new_tasks += 1

                        # Get result
                        try:
                            _ = fut_db.result()
                        except concurrent.futures.BrokenExecutor as err:
                            LOG.critical(
                                "Updating of file %s to database failed! Error: %s",
                                updated_file,
                                err,
                            )
                            continue

                # Schedule the next set of futures for download
                for dfile in itertools.islice(iterator, len(ddone)):
                    LOG.debug("Downloading file %s...", dfile)
                    download_threads[texec.submit(getter.get, file=dfile)] = dfile
