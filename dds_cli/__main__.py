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
import functools

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
import dds_cli.account_manager
import dds_cli.data_getter
import dds_cli.data_lister
import dds_cli.data_putter
import dds_cli.data_remover
import dds_cli.directory
import dds_cli.project_creator
import dds_cli.auth
import dds_cli.project_status
import dds_cli.utils
from dds_cli.options import args, flags, opts


####################################################################################################
# START LOGGING CONFIG ###################################################### START LOGGING CONFIG #
####################################################################################################

LOG = logging.getLogger()


## # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
#                                                                                                  #
#                          MMMM   MMMM      AAAA      II   NNNN    NN                              #
#                          MM MM MM MM     AA  AA     II   NN NN   NN                              #
#                          MM  MMM  MM    AA    AA    II   NN  NN  NN                              #
#                          MM   M   MM   AAAAAAAAAA   II   NN   NN NN                              #
#                          MM       MM   AA      AA   II   NN    NNNN                              #
#                                                                                                  #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # ##


# Print header to STDERR
dds_cli.utils.stderr_console.print(
    "[green]     ︵",
    "\n[green] ︵ (  )   ︵",
    "\n[green](  ) ) (  (  )[/]   [bold]SciLifeLab Data Delivery System",
    "\n[green] ︶  (  ) ) ([/]    [blue][link={0}]{0}[/link]".format(dds_cli.__url__),
    f"\n[green]      ︶ (  )[/]    [dim]Version {dds_cli.__version__}",
    "\n[green]          ︶\n",
    highlight=False,
)

# -- dds -- #
@click.group()
@click.option(
    "-v", "--verbose", is_flag=True, default=False, help="Print verbose output to the console."
)
@click.option("-l", "--log-file", help="Save a log to a file.", metavar="<filename>")
@click.option(
    "--no-prompt", is_flag=True, default=False, help="Run without any interactive features."
)
@click.version_option(version=dds_cli.__version__, prog_name=dds_cli.__title__)
@click.pass_context
def dds_main(click_ctx, verbose, log_file, no_prompt):
    """SciLifeLab Data Delivery System (DDS) command line interface.

    Access token is saved in a .dds_cli_token file in the home directory.
    """
    if "--help" not in sys.argv:
        # Set the base logger to output DEBUG
        LOG.setLevel(logging.DEBUG)

        # Set up logs to the console
        LOG.addHandler(
            rich.logging.RichHandler(
                level=logging.DEBUG if verbose else logging.INFO,
                console=dds_cli.utils.stderr_console,
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

        # Create context object
        click_ctx.obj = {"NO_PROMPT": no_prompt}


# ************************************************************************************************ #
# COMMON OPTIONS - MAIN **************************************************** COMMON OPTIONS - MAIN #
# ************************************************************************************************ #


def common_options_project_contents(f):
    """Common options used when listing project contents."""
    options = [flags.users, flags.json, flags.tree]
    return functools.reduce(lambda x, opt: opt(x), options, f)


# ************************************************************************************************ #
# MAIN DDS COMMANDS ************************************************************ MAIN DDS COMMANDS #
# ************************************************************************************************ #

# -- dds ls -- #
@dds_main.command(name="ls")
# Positional args
@click.argument("project", metavar="[PROJECT ID]", nargs=1, required=False)
@click.argument("folder", nargs=1, required=False)
# Options
@opts.username_optional
@opts.sort_optional
# Flags
@flags.projects
@flags.size
@flags.usage
# Common
@common_options_project_contents  # users, json, tree
@click.pass_obj
def ls(click_ctx, project, folder, username, sort, projects, size, usage, tree, users, json):
    """
    List your projects and project files.

    To list all projects, run `dds ls` without any arguments.

    Specify a Project ID to list the files within a project.
    You can also follow this with a subfolder path to show files within that folder.
    """
    LOG.info(click_ctx)
    try:
        # List all projects if project is None and all files if project spec
        if project is None:
            with dds_cli.data_lister.DataLister(
                project=project,
                show_usage=usage,
                username=username,
                no_prompt=click_ctx.get("NO_PROMPT", False),
                json=json,
            ) as lister:
                projects = lister.list_projects(sort_by=sort)
                if json:
                    dds_cli.utils.console.print_json(data=projects)
                else:
                    # If an interactive terminal, ask user if they want to view files for a project
                    if sys.stdout.isatty() and not lister.no_prompt:
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
                no_prompt=click_ctx.get("NO_PROMPT", False),
                json=json,
            ) as lister:
                if json:
                    json_output = {"project_name": project}
                    if users:
                        user_list = lister.list_users()
                        json_output["users"] = user_list

                    if tree:
                        folders = lister.list_recursive(show_size=size)
                        json_output["project_files_and_directories"] = folders
                    else:
                        LOG.warning(
                            "JSON output for file listing only possible for the complete file tree. "
                            "Please use the '--tree' option to view complete contens in JSON or remove the '--json' "
                            "option to list files interactively"
                        )
                    dds_cli.utils.console.print_json(data=json_output)
                else:
                    if users:
                        user_list = lister.list_users()

                    if tree:
                        folders = lister.list_recursive(show_size=size)
                    else:
                        folders = lister.list_files(folder=folder, show_size=size)

                        # If an interactive terminal, ask user if they want to view files for a proj
                        if sys.stdout.isatty() and (not lister.no_prompt) and len(folders) > 0:
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
####################################################################################################
## AUTH #################################################################################### AUTH ##
####################################################################################################
####################################################################################################


@dds_main.group(name="auth", no_args_is_help=True)
@click.pass_obj
def auth_group_command(_):
    """Group command: dds auth. Manage the saved authentication token."""


# ************************************************************************************************ #
# AUTH COMMANDS ******************************************************************** AUTH COMMANDS #
# ************************************************************************************************ #


# -- dds auth login -- #
@auth_group_command.command(name="login")
@opts.username_optional
@click.pass_obj
def login(click_ctx, username):
    """Renew the authentication token stored in the '.dds_cli_token' file.

    Run this command before running the cli in a non interactive fashion as this enables the longest
    possible session time before a password needs to be entered again.
    """
    no_prompt = click_ctx.get("NO_PROMPT", False)
    if no_prompt:
        LOG.warning("The --no-prompt flag is ignored for `dds auth login`")
    try:
        with dds_cli.auth.Auth(username=username):
            # Authentication token renewed in the init method.
            LOG.info("[green] :white_check_mark: Authentication token renewed![/green]")
    except (
        dds_cli.exceptions.APIError,
        dds_cli.exceptions.AuthenticationError,
        dds_cli.exceptions.DDSCLIException,
    ) as err:
        LOG.error(err)
        sys.exit(1)


# -- dds auth logout -- #
@auth_group_command.command(name="logout")
def logout():
    """Remove the saved authentication token by deleting the '.dds_cli_token' file."""
    try:
        with dds_cli.auth.Auth(username=None, authenticate=False) as authenticator:
            authenticator.logout()
            LOG.info("[green]Successfully logged out![/green]")
    except dds_cli.exceptions.DDSCLIException as err:
        LOG.error(err)
        sys.exit(1)


# -- dds auth info -- #
@auth_group_command.command(name="info")
def info():
    """Print info on saved authentication token validity and age."""
    try:
        with dds_cli.auth.Auth(username=None, authenticate=False) as authenticator:
            authenticator.check()
    except dds_cli.exceptions.DDSCLIException as err:
        LOG.error(err)
        sys.exit(1)


####################################################################################################
####################################################################################################
## USER #################################################################################### USER ##
####################################################################################################
####################################################################################################


@dds_main.group(name="user", no_args_is_help=True)
@click.pass_obj
def user_group_command(_):
    """Group command: dds user. Manage user accounts, including your own."""


# ************************************************************************************************ #
# USER COMMANDS ******************************************************************** USER COMMANDS #
# ************************************************************************************************ #

# -- dds user add -- #
@user_group_command.command(name="add", no_args_is_help=True)
# Positional args
@args.email_required
# Options
@opts.username_optional
@opts.role_required
@click.option(
    "--project",
    "-p",
    required=False,
    type=str,
    help="Existing Project you want the user to be associated to.",
)
@click.pass_obj
def add_user(click_ctx, email, username, role, project):
    """
    Add a user to the DDS system or hosted projects.

    Specify an user's email and role to associate it with projects.
    If the user doesn't exist in the system yet, an invitation email
    will be sent automatically to that person.

    """
    try:
        with dds_cli.account_manager.AccountManager(
            username=username, no_prompt=click_ctx.get("NO_PROMPT", False)
        ) as inviter:
            inviter.add_user(email=email, role=role, project=project)
            if project:
                LOG.info(
                    "Any user shown as invited would need to be added to the project "
                    "once the user has accepted the invitation and created an account in the system."
                )
    except (
        dds_cli.exceptions.AuthenticationError,
        dds_cli.exceptions.ApiResponseError,
        dds_cli.exceptions.ApiRequestError,
        dds_cli.exceptions.DDSCLIException,
    ) as err:
        LOG.error(err)
        sys.exit(1)


# -- dds user delete -- #
@user_group_command.command(name="delete", no_args_is_help=True)
# Positional args
@args.email_optional
# Options
@opts.username_optional
# Flags
@click.option(
    "--self",
    required=False,
    is_flag=True,
    help="Decommission your own user account",
)
@click.pass_obj
def delete_user(click_ctx, email, username, self):
    """
    Delete user accounts from the Data Delivery System.

    To request the removal of your own account, use the `--self` flag without any arguments.
    An e-mail will be sent to you asking to confirm the deletion.

    If you have sufficient administrative privileges, you may also delete the accounts of other users.
    Specify the e-mail address as argument to the main command to initiate the removal process.
    """
    if click_ctx.get("NO_PROMPT", False):
        pass
    else:
        if not self:
            proceed_deletion = rich.prompt.Confirm.ask(
                f"Delete Data Delivery System user account associated with {email}"
            )
        else:
            proceed_deletion = rich.prompt.Confirm.ask(
                f"Are you sure? Deleted accounts can't be restored!"
            )

    if proceed_deletion:
        try:
            with dds_cli.account_manager.AccountManager(
                username=username,
                method="delete",
                no_prompt=click_ctx.get("NO_PROMPT", False),
            ) as manager:
                if self and not email:
                    manager.delete_own_account()
                elif email and not self:
                    manager.delete_user(email=email)
                else:
                    LOG.error(
                        "You must either specify the '--self' flag or the e-mail address of the user to be deleted"
                    )
                    sys.exit(1)

        except (
            dds_cli.exceptions.AuthenticationError,
            dds_cli.exceptions.ApiResponseError,
            dds_cli.exceptions.ApiRequestError,
            dds_cli.exceptions.DDSCLIException,
        ) as err:
            LOG.error(err)
            sys.exit(1)


####################################################################################################
####################################################################################################
## PROJECT ############################################################################## PROJECT ##
####################################################################################################
####################################################################################################


@dds_main.group(name="project", invoke_without_command=True)
@click.pass_obj
def project_group_command(_):
    """Group command: dds project. Manage projects."""


# ************************************************************************************************ #
# PROJECT COMMANDS ************************************************************** PROJECT COMMANDS #
# ************************************************************************************************ #


# -- dds project ls -- #
@project_group_command.command(name="ls")
# Options
@opts.username_optional
@opts.sort_optional
# Common
@flags.json  # users, json, tree
@click.pass_context
def list_projects(ctx, username, json, sort):
    """List project contents. Calls the dds ls function."""
    LOG.info(ctx)
    ctx.invoke(ls, username=username, json=json, sort=sort)


# -- dds project create -- #
@project_group_command.command(no_args_is_help=True)
# Options
@opts.username_optional
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
    click_ctx,
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
        with dds_cli.project_creator.ProjectCreator(
            username=username, no_prompt=click_ctx.get("NO_PROMPT", False)
        ) as creator:
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


# ************************************************************************************************ #
# PROJECT SUB GROUPS ********************************************************** PROJECT SUB GROUPS #
# ************************************************************************************************ #


# STATUS ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ STATUS #
@project_group_command.group(name="status", invoke_without_command=True)  # TODO: have this?
@click.pass_obj
def project_status(_):
    """Manage project statuses."""


# -- dds project status display -- #
@project_status.command(name="display", no_args_is_help=True)
@opts.username_optional
@opts.project_required
# Flags
@click.option(
    "--show_history",
    required=False,
    is_flag=True,
    help="Show history of project statuses in addition to current status",
)
@click.pass_obj
def display_project_status(click_ctx, username, project, show_history):
    """Display and Update project status."""
    try:
        with dds_cli.project_status.ProjectStatusManager(
            username=username, project=project, no_prompt=click_ctx.get("NO_PROMPT", False)
        ) as updater:
            updater.get_status(show_history)
    except (
        dds_cli.exceptions.APIError,
        dds_cli.exceptions.AuthenticationError,
        dds_cli.exceptions.DDSCLIException,
    ) as err:
        LOG.error(err)
        sys.exit(1)


# -- dds project status release -- #
@project_status.command(name="release", no_args_is_help=True)
# Options
@opts.username_optional
@opts.project_required
@click.option(
    "--deadline",
    required=False,
    type=int,
    help="Deadline in days when releasing a project",
)
@click.pass_obj
def release_project(click_ctx, username, project, deadline):
    """Make project available for user download."""
    try:
        with dds_cli.project_status.ProjectStatusManager(
            username=username, project=project, no_prompt=click_ctx.get("NO_PROMPT", False)
        ) as updater:
            updater.update_status(new_status="Available", deadline=deadline)
    except (
        dds_cli.exceptions.APIError,
        dds_cli.exceptions.AuthenticationError,
        dds_cli.exceptions.DDSCLIException,
    ) as err:
        LOG.error(err)
        sys.exit(1)


# -- dds project status retract -- #
@project_status.command(name="retract", no_args_is_help=True)
# Options
@opts.username_optional
@opts.project_required
@click.pass_obj
def retract_project(click_ctx, username, project):
    """Retract a project available for download to add more data."""
    try:
        with dds_cli.project_status.ProjectStatusManager(
            username=username, project=project, no_prompt=click_ctx.get("NO_PROMPT", False)
        ) as updater:
            updater.update_status(new_status="In Progress")
    except (
        dds_cli.exceptions.APIError,
        dds_cli.exceptions.AuthenticationError,
        dds_cli.exceptions.DDSCLIException,
    ) as err:
        LOG.error(err)
        sys.exit(1)


# -- dds project status archive -- #
@project_status.command(name="archive", no_args_is_help=True)
# Options
@opts.username_optional
@opts.project_required
@click.pass_obj
def archive_project(click_ctx, username, project):
    """Manually archive a released project and delete all its data."""
    try:
        with dds_cli.project_status.ProjectStatusManager(
            username=username, project=project, no_prompt=click_ctx.get("NO_PROMPT", False)
        ) as updater:
            updater.update_status(new_status="Archived")
    except (
        dds_cli.exceptions.APIError,
        dds_cli.exceptions.AuthenticationError,
        dds_cli.exceptions.DDSCLIException,
    ) as err:
        LOG.error(err)
        sys.exit(1)


# -- dds project status delete -- #
@project_status.command(name="delete", no_args_is_help=True)
# Options
@opts.username_optional
@opts.project_required
@click.pass_obj
def delete_project(click_ctx, username, project):
    """Delete an unreleased project and all its data."""
    try:
        with dds_cli.project_status.ProjectStatusManager(
            username=username, project=project, no_prompt=click_ctx.get("NO_PROMPT", False)
        ) as updater:
            updater.update_status(new_status="Deleted")
    except (
        dds_cli.exceptions.APIError,
        dds_cli.exceptions.AuthenticationError,
        dds_cli.exceptions.DDSCLIException,
    ) as err:
        LOG.error(err)
        sys.exit(1)


# -- dds project status abort -- #
@project_status.command(name="abort", no_args_is_help=True)
# Options
@opts.username_optional
@opts.project_required
@click.pass_obj
def abort_project(click_ctx, username, project):
    """Abort a released project to delete all its data."""
    try:
        with dds_cli.project_status.ProjectStatusManager(
            username=username, project=project, no_prompt=click_ctx.get("NO_PROMPT", False)
        ) as updater:
            updater.update_status(new_status="Archived", is_aborted=True)
    except (
        dds_cli.exceptions.APIError,
        dds_cli.exceptions.AuthenticationError,
        dds_cli.exceptions.DDSCLIException,
    ) as err:
        LOG.error(err)
        sys.exit(1)


# ACCESS ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ ACCESS #
@project_group_command.group(name="access", invoke_without_command=True)  # TODO: have this?
@click.pass_obj
def project_access(_):
    """Manage project statuses."""


# -- dds project access grant -- #
@project_access.command(name="grant", no_args_is_help=True)
# Options
@opts.username_optional
@opts.project_required
@click.option(
    "--email",
    "-e",
    required=True,
    type=str,
    help="Email of the user you would like to invite.",
)
# Flags
@click.option(
    "--owner",
    required=False,
    is_flag=True,
    help="Grant access as project owner. If not specified, the user gets Researcher permissions within the project.",
)
@click.pass_obj
def grant_project_access(click_ctx, username, project, email, owner):
    """Grant user access to a project."""
    try:
        with dds_cli.account_manager.AccountManager(
            username=username, no_prompt=click_ctx.get("NO_PROMPT", False)
        ) as granter:
            role = "Researcher"
            if owner:
                role = "Project Owner"
            granter.add_user(email=email, role=role, project=project)
            if project:
                LOG.info(
                    "Any user shown as invited would need to be added to the project once the user "
                    "has accepted the invitation and created an account in the system."
                )
    except (
        dds_cli.exceptions.AuthenticationError,
        dds_cli.exceptions.ApiResponseError,
        dds_cli.exceptions.ApiRequestError,
        dds_cli.exceptions.DDSCLIException,
    ) as err:
        LOG.error(err)
        sys.exit(1)


# -- dds project access revoke -- #
@project_access.command(name="revoke", no_args_is_help=True)
# Options
@opts.username_optional
@opts.project_required
@click.option(
    "--email",
    "-e",
    required=True,
    type=str,
    help="Email of the user for whom project access is to be revoked.",
)
@click.pass_obj
def revoke_project_access(click_ctx, username, project, email):
    """Revoke user access to a project."""
    try:
        with dds_cli.account_manager.AccountManager(
            username=username, no_prompt=click_ctx.get("NO_PROMPT", False)
        ) as revoker:
            revoker.revoke_project_access(project, email)
    except (
        dds_cli.exceptions.APIError,
        dds_cli.exceptions.AuthenticationError,
        dds_cli.exceptions.DDSCLIException,
    ) as err:
        LOG.error(err)
        sys.exit(1)


####################################################################################################
####################################################################################################
## DATA #################################################################################### DATA ##
####################################################################################################
####################################################################################################


@dds_main.group(name="data", invoke_without_command=True)
@click.pass_obj
def data_group_command(_):
    """Group command: dds project. Manage projects."""


# ************************************************************************************************ #
# DATA COMMANDS ******************************************************************** DATA COMMANDS #
# ************************************************************************************************ #


# -- dds data put -- #
@data_group_command.command(name="put", no_args_is_help=True)
# Options
@opts.username_optional
@click.option(
    "--project",
    "-p",
    required=True,
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
@opts.num_threads_optional
# Flags
@flags.silent
@click.pass_obj
def put_data(
    click_ctx,
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
            no_prompt=click_ctx.get("NO_PROMPT", False),
        )
    except (dds_cli.exceptions.AuthenticationError, dds_cli.exceptions.UploadError) as err:
        LOG.error(err)
        sys.exit(1)


# -- dds data get -- #
@data_group_command.command(name="get", no_args_is_help=True)
@opts.username_optional
@opts.num_threads_optional
@click.option(
    "--project",
    "-p",
    required=True,
    type=str,
    help="Project ID from which you're downloading data.",
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
def get_data(
    click_ctx,
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
        sys.exit(1)

    try:
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
            no_prompt=click_ctx.get("NO_PROMPT", False),
        ) as getter:

            with rich.progress.Progress(
                "{task.description}",
                rich.progress.BarColumn(bar_width=None),
                " • ",
                "[progress.percentage]{task.percentage:>3.1f}%",
                refresh_per_second=2,
                console=dds_cli.utils.stderr_console,
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
                        LOG.debug(f"Starting: {file}")
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
                            LOG.debug(
                                f"Future done: {downloaded_file}",
                            )

                            # Get result
                            try:
                                file_downloaded = dfut.result()
                                LOG.debug(
                                    f"Download of {downloaded_file} successful: {file_downloaded}"
                                )
                            except concurrent.futures.BrokenExecutor as err:
                                LOG.critical(
                                    f"Download of file {downloaded_file} failed! Error: {err}"
                                )
                                continue

                            new_tasks += 1
                            progress.advance(task_dwnld)

                        # Schedule the next set of futures for download
                        for next_file in itertools.islice(iterator, new_tasks):
                            LOG.debug(f"Starting: {next_file}")
                            # Execute download
                            download_threads[
                                texec.submit(
                                    getter.download_and_verify,
                                    file=next_file,
                                    progress=progress,
                                )
                            ] = next_file
    except (
        dds_cli.exceptions.InvalidMethodError,
        OSError,
        dds_cli.exceptions.TokenNotFoundError,
        dds_cli.exceptions.AuthenticationError,
        dds_cli.exceptions.ApiRequestError,
        dds_cli.exceptions.ApiResponseError,
        SystemExit,
        dds_cli.exceptions.DDSCLIException,
        dds_cli.exceptions.NoDataError,
        dds_cli.exceptions.DownloadError,
    ) as err:
        LOG.error(err)
        sys.exit(1)


# -- dds data ls -- #
@data_group_command.command(name="ls", no_args_is_help=True)
# Options
@opts.username_optional
@opts.project_required
@click.option(
    "--folder",
    "-f",
    required=False,
    type=str,
    help="List contents in this project folder.",
)
# Flags
@flags.size  # used for listing project contents
# Common
@common_options_project_contents  # users, json, tree
@click.pass_context
def list_data(ctx, username, project, folder, size, tree, users, json):
    """List project contents. Same as dds ls [PROJECT ID]."""
    ctx.invoke(
        ls,
        username=username,
        project=project,
        folder=folder,
        size=size,
        tree=tree,
        users=users,
        json=json,
    )


# -- dds data rm -- #
@data_group_command.command(name="rm", no_args_is_help=True)
# Options
@opts.username_optional
@opts.project_required
@click.option(
    "--file", "-f", required=False, type=str, multiple=True, help="Path to file to remove."
)
@click.option(
    "--folder", "-fl", required=False, type=str, multiple=True, help="Path to folder to remove."
)
# Flags
@click.option(
    "--rm-all",
    "-a",
    is_flag=True,
    default=False,
    help="Remove all project contents.",
)
@click.pass_obj
def rm_data(click_ctx, username, project, file, folder, rm_all):
    """Delete the files within a project."""
    no_prompt = click_ctx.get("NO_PROMPT", False)

    # Either all or a file
    if rm_all and (file or folder):
        LOG.error("The options '--rm-all' and '--file'/'--folder' cannot be used together.")
        sys.exit(1)

    # Will not delete anything if no file or folder specified
    if project and not any([rm_all, file, folder]):
        LOG.error(
            "One of the options must be specified to perform data deletion: "
            "'--rm-all' / '--file' / '--folder'."
        )
        sys.exit(1)

    # Warn if trying to remove all contents
    if rm_all:
        if no_prompt:
            LOG.warning(f"Deleting all files within project '{project}'")
        else:
            if not rich.prompt.Confirm.ask(
                f"Are you sure you want to delete all files within project '{project}'?"
            ):
                LOG.info("Probably for the best. Exiting.")
                sys.exit(0)

    try:
        with dds_cli.data_remover.DataRemover(
            project=project,
            username=username,
            no_prompt=no_prompt,
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
