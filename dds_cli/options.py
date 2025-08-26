"""Click DDS options used multiple times in __main__.py."""

# Imports
import pathlib
import click
from dds_cli.utils import multiple_help_text


# Args used multiple times
def email_arg(required, email="email", metavar="[EMAIL]", nargs=1):
    """
    Email positional argument standard definition.

    Use as decorator for commands.
    """
    return click.argument(email, metavar=metavar, nargs=nargs, type=str, required=required)


# Options used multiple times


def destination_option(
    help_message, option_type, long="--destination", short="-d", name="destination", required=False
):
    """Destination option standard definition.

    Use as decorator for commands.
    """
    return click.option(
        long,
        short,
        name,
        required=required,
        type=option_type,
        multiple=False,
        help=help_message,
    )


def email_option(help_message, long="--email", short="-e", name="email", required=True):
    """
    Email option standard definition.

    Use as decorator for commands.
    """
    return click.option(
        long,
        short,
        name,
        required=required,
        type=str,
        help=help_message,
    )


def folder_option(
    help_message, long="--folder", short="-f", name="folder", required=False, multiple=False
):
    """
    Folder option standard definition.

    Use as decorator for commands.
    """
    if multiple:
        help_message += multiple_help_text(item="folder")
    return click.option(
        long,
        short,
        name,
        required=required,
        type=str,
        multiple=multiple,
        help=help_message,
    )


def num_threads_option(
    long="--num-threads",
    short="-nt",
    name="num_threads",
    required=False,
    default=4,
    show_default=True,
    help_message="Number of parallel threads to perform the delivery",
):
    """
    Num threads option standard definition.

    Use as decorator for commands.
    """
    return click.option(
        long,
        short,
        name,
        required=required,
        default=default,
        show_default=show_default,
        type=click.IntRange(1, 32),
        help=help_message,
    )


def project_option(
    required, long="--project", short="-p", name="project", help_message="Project ID."
):
    """
    Project option standard definition.

    Use as decorator for commands.
    """
    return click.option(
        long,
        short,
        name,
        required=required,
        type=str,
        help=help_message,
    )


def sort_projects_option(
    long="--sort",
    name="sort",
    choices=("id", "title", "pi", "status", "updated", "size", "usage", "cost"),
    case_sensitive=False,
    default="Updated",
    required=False,
    help_message="Which column to sort the project list by.",
):
    """
    Sort option standard definition.

    Use as decorator for commands where you wish to sort the projects.
    """
    return click.option(
        long,
        name,
        type=click.Choice(
            choices=choices,
            case_sensitive=case_sensitive,
        ),
        default=default,
        required=required,
        help=help_message,
    )


def source_option(
    help_message, option_type, long="--source", short="-s", name="source", required=False
):
    """
    Source option standard definition.

    Use as decorator for commands.
    """
    return click.option(
        long,
        short,
        name,
        required=required,
        type=option_type,
        multiple=True,
        help=help_message + multiple_help_text(item="source"),
    )


def source_path_file_option(
    long="--source-path-file",
    short="-spf",
    name="source_path_file",
    required=False,
    help_message="File containing path to files or directories.",
):
    """
    Source path file option standard definition.

    Use as decorator for commands.
    """
    return click.option(
        long,
        short,
        name,
        required=required,
        type=click.Path(exists=True, path_type=pathlib.Path),
        multiple=False,
        help=help_message,
    )


def token_path_option(
    long="--token-path",
    short="-tp",
    name="token_path",
    required=False,
    help_message=(
        "The path where the authentication token will be stored. "
        "For a normal use-case, this should not be needed."
    ),
):
    """
    token path option standard definition.

    Use as decorator for commands.
    """
    return click.option(
        long,
        short,
        name,
        required=required,
        type=str,
        help=help_message,
    )


def username_option(help_message, long="--username", short="-u", name="username", required=False):
    """
    Username option standard definition.

    Use as decorator for commands.
    """
    return click.option(
        long,
        short,
        name,
        required=required,
        type=str,
        help=help_message,
    )


# Flags
def break_on_fail_flag(
    help_message,
    long="--break-on-fail",
    name="break_on_fail",
    show_default=True,
):
    """
    Break on fail flag standard definition.

    Use as decorator for commands.
    """
    return click.option(
        long,
        name,
        is_flag=True,
        default=False,
        show_default=show_default,
        help=help_message,
    )


def json_flag(help_message, long="--json", name="json", show_default=True):
    """
    Json flag standard definition.

    Use as decorator for commands.
    """
    return click.option(
        long,
        name,
        is_flag=True,
        default=False,
        show_default=show_default,
        help=help_message,
    )


def nomail_flag(
    help_message,
    long="--no-mail",
    name="no_mail",
    show_default=False,
):
    """
    No-email flag standard definition.

    Use as decorator for commands.
    """
    return click.option(
        long,
        name,
        is_flag=True,
        default=False,
        show_default=show_default,
        help=help_message,
    )


def silent_flag(
    help_message,
    long="--silent",
    name="silent",
    show_default=True,
):
    """
    Silent flag standard definition.

    Use as decorator for commands.
    """
    return click.option(
        long,
        name,
        is_flag=True,
        default=False,
        show_default=show_default,
        help=help_message,
    )


def size_flag(help_message, long="--size", name="size", show_default=True):
    """
    Size flag standard definition.

    Use as decorator for commands.
    """
    return click.option(
        long,
        name,
        is_flag=True,
        default=False,
        show_default=show_default,
        help=help_message,
    )


def tree_flag(help_message, long="--tree", name="tree", show_default=True):
    """
    Tree flag standard definition.

    Use as decorator for commands.
    """
    return click.option(
        long,
        name,
        is_flag=True,
        default=False,
        show_default=show_default,
        help=help_message,
    )


def usage_flag(help_message, long="--usage", name="usage", show_default=True):
    """
    Usage flag standard definition.

    Use as decorator for commands where displaying the usage may be desired.
    """
    return click.option(
        long, name, is_flag=True, default=False, show_default=show_default, help=help_message
    )


def users_flag(
    help_message,
    long="--users",
    name="users",
    show_default=True,
):
    """
    Users flag standard definition.

    Use as a decorator for commands.
    """
    return click.option(
        long,
        name,
        is_flag=True,
        default=False,
        show_default=show_default,
        help=help_message,
    )
