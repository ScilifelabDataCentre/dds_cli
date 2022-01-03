"""Keyword arguments / Options."""

import click

# Options

username_optional = click.option(
    "--username",
    "-u",
    required=False,
    type=str,
    help="Your Data Delivery System username.",
)


sort_optional = click.option(
    "--sort",
    type=click.Choice(
        choices=["id", "title", "pi", "status", "updated", "size", "usage", "cost"],
        case_sensitive=False,
    ),
    default="Updated",
    required=False,
    help="Which column to sort the project list by.",
)

num_threads_optional = click.option(
    "--num-threads",
    "-nt",
    required=False,
    multiple=False,
    default=4,
    show_default=True,
    type=click.IntRange(1, 32),
    help="Number of parallel threads to perform the delivery",
)

# Required


project_required = click.option(
    "--project",
    "-p",
    required=True,
    type=str,
    help="Project ID.",
)
