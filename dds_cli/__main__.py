"""CLI for the Data Delivery System."""

####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
####################################################################################################

# Standard library
import concurrent.futures
import itertools
import logging
import os
import sys

# Installed
import click
import click_pathlib
import rich
import rich.logging
import rich.progress
import rich.prompt
import questionary

# Own modules
import dds_cli
import dds_cli.account_adder
import dds_cli.data_getter
import dds_cli.data_lister
import dds_cli.data_putter
import dds_cli.data_remover
import dds_cli.directory
import dds_cli.project_creator
import dds_cli.session
import dds_cli.utils


####################################################################################################
# START LOGGING CONFIG ###################################################### START LOGGING CONFIG #
####################################################################################################

LOG = logging.getLogger()

####################################################################################################
# MAIN ###################################################################################### MAIN #
####################################################################################################

# Print header to STDERR
stderr = dds_cli.utils.console
stderr.print(
    "[green]     ︵",
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
def dds_main(_, verbose, log_file):
    """The SciLifeLab Data Delivery System (DDS) command line interface

    Access token is saved in a .dds_cli_token file in the home directory.
    """
    if "--help" not in sys.argv:

        # Set the base logger to output DEBUG
        LOG.setLevel(logging.DEBUG)

        # Set up logs to the console
        LOG.addHandler(
            rich.logging.RichHandler(
                level=logging.DEBUG if verbose else logging.INFO,
                console=dds_cli.utils.console,
                show_time=False,
                markup=True,
                show_path=verbose,
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


####################################################################################################
# INVITE USER ######################################################################## INVITE USER #
####################################################################################################


@dds_main.command()
@click.option(
    "--username",
    "-u",
    required=False,
    type=str,
    help="Your Data Delivery System username.",
)
@click.option(
    "--email", "-e", required=True, type=str, help="Email of the user you would like to invite."
)
@click.option(
    "--role",
    "-r",
    required=True,
    type=click.Choice(
        choices=["Super Admin", "Unit Admin", "Unit Personnel", "Project Owner", "Researcher"],
        case_sensitive=False,
    ),
    help="Type of account.",
)
@click.option(
    "--project",
    "-p",
    required=False,
    type=str,
    help="Existing Project you want the user to be associated to.",
)
@click.pass_obj
def add_user(_, username, email, role, project):
    """Add user to DDS, sending an invitation email to that person."""
    # All exceptions caught within
    with dds_cli.account_adder.AccountAdder(username=username) as inviter:
        inviter.add_user(email=email, role=role, project=project)
        if project:
            LOG.info(
                "Any user shown as invited would need to be added to the project "
                "once the user has accepted the invitation and created an account in the system."
            )


####################################################################################################
# PUT ######################################################################################## PUT #
####################################################################################################


@dds_main.command()
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
    _,
    username,
    project,
    source,
    source_path_file,
    break_on_fail,
    overwrite,
    num_threads,
    silent,
):
    """Process and upload specified files to the cloud."""
    try:
        dds_cli.data_putter.put(
            username=username,
            project=project,
            source=source,
            source_path_file=source_path_file,
            break_on_fail=break_on_fail,
            overwrite=overwrite,
            num_threads=num_threads,
            silent=silent,
        )
    except (dds_cli.exceptions.AuthenticationError, dds_cli.exceptions.UploadError) as err:
        LOG.error(err)
        sys.exit(1)


####################################################################################################
# LIST ###################################################################################### LIST #
####################################################################################################


@dds_main.command()
@click.argument("project", metavar="[PROJECT ID]", nargs=1, required=False)
@click.argument("folder", nargs=1, required=False)
@click.option("--projects", "-lp", is_flag=True, help="List all project connected to your account.")
@click.option("--size", "-s", is_flag=True, default=False, help="Show size of project contents.")
@click.option(
    "--username", "-u", required=False, type=str, help="Your Data Delivery System username."
)
@click.option(
    "--usage",
    is_flag=True,
    default=False,
    show_default=True,
    help="Show the usage for a specific facility, in GBHours and cost.",
)
@click.option(
    "--sort",
    type=click.Choice(
        choices=["id", "title", "pi", "status", "updated", "size", "usage", "cost"],
        case_sensitive=False,
    ),
    default="Updated",
    required=False,
    help="Which column to sort the project list by.",
)
@click.option(
    "-t", "--tree", is_flag=True, default=False, help="Display the entire project(s) directory tree"
)
@click.option(
    "--users",
    is_flag=True,
    default=False,
    help="Display users associated with a project(Requires a project id)",
)
@click.pass_obj
def ls(_, project, folder, projects, size, username, usage, sort, tree, users):
    """
    List your projects and project files.

    To list all projects, run `dds ls` without any arguments.

    Specify a Project ID to list the files within a project.
    You can also follow this with a subfolder path to show files within that folder.
    """
    try:
        # List all projects if project is None and all files if project spec
        if project is None:
            with dds_cli.data_lister.DataLister(
                project=project,
                show_usage=usage,
                username=username,
            ) as lister:
                projects = lister.list_projects(sort_by=sort)

                # If an interactive terminal, ask user if they want to view files for a project
                if sys.stdout.isatty():
                    project_ids = [p["Project ID"] for p in projects]
                    LOG.info(
                        "Would you like to view files in a specific project? Leave blank to exit."
                    )
                    # Keep asking until we get a valid response
                    while project not in project_ids:
                        try:
                            project = questionary.autocomplete(
                                "Project ID:",
                                choices=project_ids,
                                validate=lambda x: x in project_ids or x == "",
                                style=dds_cli.dds_questionary_styles,
                            ).unsafe_ask()
                            assert project and project != ""

                        # If didn't enter anything, convert to None and exit
                        except (KeyboardInterrupt, AssertionError):
                            break

        # List all files in a project if we know a project ID
        if project:
            with dds_cli.data_lister.DataLister(
                project=project,
                username=username,
                tree=tree,
            ) as lister:
                if users:
                    user_list = lister.list_users()
                    if not sys.stdout.isatty():
                        if user_list:
                            LOG.info("Project has the following users")
                            for user in user_list:
                                LOG.info(user["User Name"], user["Primary email"])
                else:
                    if tree:
                        lister.list_recursive(show_size=size)
                    else:
                        folders = lister.list_files(folder=folder, show_size=size)

                        # If an interactive terminal, ask user if they want to view files for a proj
                        if sys.stdout.isatty() and len(folders) > 0:
                            LOG.info(
                                "Would you like to view files within a directory? "
                                "Leave blank to exit."
                            )
                            last_folder = None
                            while folder is None or folder != last_folder:
                                last_folder = folder

                                try:
                                    folder = questionary.autocomplete(
                                        "Folder:",
                                        choices=folders,
                                        validate=lambda x: x in folders or x == "",
                                        style=dds_cli.dds_questionary_styles,
                                    ).unsafe_ask()
                                    assert folder != ""
                                    assert folder is not None
                                # If didn't enter anything, convert to None and exit
                                except (KeyboardInterrupt, AssertionError):
                                    break

                                # Prepend existing file path
                                if last_folder is not None and folder is not None:
                                    folder = os.path.join(last_folder, folder)

                                # List files
                                folders = lister.list_files(folder=folder, show_size=size)

                                if len(folders) == 0:
                                    break

    except (dds_cli.exceptions.NoDataError) as err:
        LOG.warning(err)
        sys.exit(0)
    except (dds_cli.exceptions.APIError, dds_cli.exceptions.AuthenticationError) as err:
        LOG.error(err)
        sys.exit(1)


####################################################################################################
# DELETE ################################################################################## DELETE #
####################################################################################################


@dds_main.command()
@click.argument("proj_arg", required=False)
@click.option("--project", "-p", required=False, type=str, help="Project ID.")
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
@click.pass_obj
def rm(_, proj_arg, project, username, rm_all, file, folder):
    """Delete the files within a project."""
    # One of proj_arg or project is required
    if all(x is None for x in [proj_arg, project]):
        LOG.error("No project specified, cannot remove anything.")
        sys.exit(1)

    # Either all or a file
    if rm_all and (file or folder):
        LOG.error("The options '--rm-all' and '--file'/'--folder' cannot be used together.")
        sys.exit(1)

    project = proj_arg if proj_arg is not None else project

    # Will not delete anything if no file or folder specified
    if project and not any([rm_all, file, folder]):
        LOG.error(
            "One of the options must be specified to perform data deletion: "
            "'--rm-all' / '--file' / '--folder'."
        )
        sys.exit(1)

    # Warn if trying to remove all contents
    if rm_all:
        if not rich.prompt.Confirm.ask(
            f"Are you sure you want to delete all files within project '{project}'?"
        ):
            LOG.info("Probably for the best. Exiting.")
            sys.exit(0)

    try:
        with dds_cli.data_remover.DataRemover(
            project=project,
            username=username,
        ) as remover:

            if rm_all:
                remover.remove_all()

            elif file:
                remover.remove_file(files=file)

            elif folder:
                remover.remove_folder(folder=folder)
    except (
        dds_cli.exceptions.AuthenticationError,
        dds_cli.exceptions.APIError,
        dds_cli.exceptions.DDSCLIException,
    ) as err:
        LOG.error(err)
        sys.exit(1)


####################################################################################################
# GET ######################################################################################## GET #
####################################################################################################


@dds_main.command()
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
    help="Path to file or directory.",
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
    _,
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
    """Download specified files from the cloud and restores the original format."""
    if get_all and (source or source_path_file):
        LOG.error(
            "Flag '--get-all' cannot be used together with options '--source'/'--source-path-fail'."
        )
        os._exit(1)

    # Begin delivery
    with dds_cli.data_getter.DataGetter(
        username=username,
        project=project,
        get_all=get_all,
        source=source,
        source_path_file=source_path_file,
        break_on_fail=break_on_fail,
        destination=destination,
        silent=silent,
        verify_checksum=verify_checksum,
    ) as getter:

        with rich.progress.Progress(
            "{task.description}",
            rich.progress.BarColumn(bar_width=None),
            " • ",
            "[progress.percentage]{task.percentage:>3.1f}%",
            refresh_per_second=2,
            console=dds_cli.utils.console,
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


###################################################################################
# CREATE ################################################################# CREATE #
###################################################################################
@dds_main.command(no_args_is_help=True)
@click.option(
    "--username",
    "-u",
    required=False,
    type=str,
    help="Your Data Delivery System username.",
)
@click.option(
    "--title",
    "-t",
    required=True,
    type=str,
    help="The title of the project",
)
@click.option(
    "--description",
    "-d",
    required=True,
    type=str,
    help="A description of the project",
)
@click.option(
    "--principal-investigator",
    "-pi",
    required=True,
    type=str,
    help="The name of the Principal Investigator",
)
@click.option(
    "--is_sensitive",
    required=False,
    is_flag=True,
    help="Indicate if the Project includes sensitive data",
)
@click.option(
    "--owner",
    required=False,
    multiple=True,
    help="Email of a user to be added to the project as Project Owner",
)
@click.option(
    "--researcher",
    required=False,
    multiple=True,
    help="Email of a user to be added to the project as Researcher",
)
@click.pass_obj
def create(
    _,
    username,
    title,
    description,
    principal_investigator,
    is_sensitive,
    owner,
    researcher,
):
    """Create a project."""
    try:
        with dds_cli.project_creator.ProjectCreator(username=username) as creator:
            emails_roles = []
            if owner or researcher:
                email_overlap = set(owner) & set(researcher)
                if email_overlap:
                    LOG.info(
                        f"The email(s) {email_overlap} specified as both owner and researcher! "
                        "Please specify a unique role for each email."
                    )
                    sys.exit(1)
                if owner:
                    emails_roles.extend([{"email": x, "role": "Project Owner"} for x in owner])
                if researcher:
                    emails_roles.extend([{"email": x, "role": "Researcher"} for x in researcher])

            created, project_id, user_addition_messages, err = creator.create_project(
                title=title,
                description=description,
                principal_investigator=principal_investigator,
                sensitive=is_sensitive,
                users_to_add=emails_roles,
            )
            if created:
                LOG.info(
                    f"Project created with id: {project_id}",
                )
                if user_addition_messages:
                    for msg in user_addition_messages:
                        LOG.info(msg)
                        LOG.info(
                            "Any user shown as invited would need to be "
                            "added to the project once the user has accepted "
                            "the invitation and created an account in the system."
                        )
    except (
        dds_cli.exceptions.APIError,
        dds_cli.exceptions.AuthenticationError,
        dds_cli.exceptions.DDSCLIException,
    ) as err:
        LOG.error(err)
        sys.exit(1)


###################################################################################
# SESSION ############################################################### SESSION #
###################################################################################
@dds_main.command()
@click.option(
    "--username",
    "-u",
    required=True,
    type=str,
    help="Your Data Delivery System username.",
)
@click.option(
    "--check",
    "-c",
    required=False,
    is_flag=True,
    help="Instead of renewing the session, only check if the session is valid and report the token age.",
)
@click.pass_obj
def session(_, username, check):
    """Renew the access token stored in the '.dds_cli_token'. Run this command before
    running the cli in a non interactive fashion as this enables the longest possible session time
    before a password needs to be entered again.
    """
    try:
        with dds_cli.session.Session(username=username, check=check) as session:
            if check:
                session.check()
            else:
                # Session renewed in the init method.
                LOG.info("[green] :white_check_mark: Session renewed![/green]")
    except (
        dds_cli.exceptions.APIError,
        dds_cli.exceptions.AuthenticationError,
        dds_cli.exceptions.DDSCLIException,
    ) as err:
        LOG.error(err)
        sys.exit(1)
