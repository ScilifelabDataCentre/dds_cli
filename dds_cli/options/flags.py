"""Flags."""

import click

users = click.option(
    "--users",
    is_flag=True,
    default=False,
    help="Display users associated with a project(Requires a project id)",
)


json = click.option(
    "--json",
    is_flag=True,
    default=False,
    help="Output in JSON format",
)

tree = click.option(
    "--tree",
    "-t",
    is_flag=True,
    default=False,
    help="Display the entire project(s) directory tree",
)


size = click.option(
    "--size", "-s", is_flag=True, default=False, help="Show size of project contents."
)

usage = click.option(
    "--usage",
    is_flag=True,
    default=False,
    show_default=True,
    help=(
        "Show the usage for available projects, in GBHours and cost. "
        "No effect when specifying a project id."
    ),
)

silent = click.option(
    "--silent",
    is_flag=True,
    default=False,
    show_default=True,
    help="Turn off progress bar for each individual file. Summary bars still visible.",
)
