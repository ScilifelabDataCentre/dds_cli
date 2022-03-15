"""DDS CLI utils module."""

import numbers
from operator import not_

import requests
import rich.console
import simplejson
from jwcrypto.common import InvalidJWEOperation
from jwcrypto.jwe import InvalidJWEData
from jwcrypto.jws import InvalidJWSObject
from jwcrypto import jwt
import http
from rich.table import Table

import dds_cli.exceptions
from dds_cli import DDSEndpoint

console = rich.console.Console()
stderr_console = rich.console.Console(stderr=True)


def sort_items(items: list, sort_by: str) -> list:
    """Sort list of dicts according to specified key."""
    return sorted(items, key=lambda i: i[sort_by])


def create_table(
    title: str,
    columns: list,
    rows: list,
    show_header: bool = True,
    header_style: str = "bold",
    show_footer: bool = False,
    caption: str = "",
) -> Table:
    """Create table."""
    # Create table
    table = Table(
        title=title,
        show_header=show_header,
        header_style=header_style,
        show_footer=show_footer,
    )

    # Add columns
    for col in columns:
        table.add_column(col, justify="left", overflow="fold")

    # Add rows
    for row in rows:
        table.add_row(
            *[
                rich.markup.escape(dds_cli.utils.format_api_response(str(row[x]), x))
                for x in columns
            ]
        )

    return table


def get_required_in_response(keys: list, response: dict) -> tuple:
    """Verify that required info is present."""
    not_returned = []
    for key in keys:
        item = response.get(key)
        if not item:
            not_returned.append(key)

    if not_returned:
        raise dds_cli.exceptions.ApiResponseError(
            message=f"The following information was returned: {not_returned}"
        )

    return tuple(response.get(x) for x in keys)


def request_get(
    endpoint,
    headers,
    params=None,
    json=None,
    error_message="API Request failed.",
    timeout=DDSEndpoint.TIMEOUT,
):
    """Perform get request."""
    try:
        response = requests.get(
            url=endpoint,
            headers=headers,
            params=params,
            json=json,
            timeout=timeout,
        )
        response_json = response.json()
    except requests.exceptions.RequestException as err:
        raise dds_cli.exceptions.ApiRequestError(message=str(err))
    except simplejson.JSONDecodeError as err:
        raise dds_cli.exceptions.ApiResponseError(message=str(err))

    # Check if response is ok.
    if not response.ok:
        message = error_message
        if response.status_code == http.HTTPStatus.INTERNAL_SERVER_ERROR:
            raise dds_cli.exceptions.ApiResponseError(message=f"{message}: {response.reason}")

        raise dds_cli.exceptions.DDSCLIException(
            message=f"{message}: {response_json.get('message', 'Unexpected error!')}"
        )

    return response_json


def parse_project_errors(errors):
    """Parse all errors related to projects."""
    msg = ""
    if errors:
        for unique_error in set(errors.values()):
            msg += unique_error
            affected_projects = [x for x, y in errors.items() if y == unique_error]
            for proj in affected_projects:
                msg += f"\n   - {proj}"

    return msg


def multiple_help_text(item):
    """Return help text for option with multiple=True."""
    return f" Use the option multiple times to specify more than one {item} [multiple]"


def get_json_response(response):
    """Get json output from requests response."""
    try:
        json_response = response.json()
    except simplejson.JSONDecodeError as err:
        raise SystemExit from err  # TODO: Change?

    return json_response


def calculate_magnitude(projects, keys, iec_standard=False):
    """Calculate magnitude of values.

    Uses the project list, obtains the values assigned to a particular key iteratively and
    calculates the best magnitude to format this set of values consistently.
    """
    # initialize the dictionary to be returned
    magnitudes = dict(zip(keys, [None] * len(keys)))

    for key in keys:
        values = [proj[key] for proj in projects]

        if all(isinstance(x, numbers.Number) for x in values):

            if key in ["Size", "Usage"] and iec_standard:
                base = 1024.0
            else:
                base = 1000.0

            # exclude values smaller than base, such that empty projects don't interfer with
            # the calculation ensures that a minimum can be calculated if no val is larger than base
            minimum = (lambda x: min(x) if x else 1)([val for val in values if val >= base])
            mag = 0

            while abs(minimum) >= base:
                mag += 1
                minimum /= base

            magnitudes[key] = mag
    return magnitudes


def format_api_response(response, key, magnitude=None, iec_standard=False):
    """Take a value e.g. bytes and reformat it to include a unit prefix."""
    if isinstance(response, str):
        return response  # pass the response if already a string

    if isinstance(response, bool):
        return ":white_heavy_check_mark:" if response else ":x:"

    if isinstance(response, numbers.Number):
        response = float(f"{response:.3g}")
        mag = 0

        if key in ["Size", "Usage"]:
            if iec_standard:
                # The IEC created prefixes such as kibi, mebi, gibi, etc.,
                # to unambiguously denote powers of 1024
                prefixlist = ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi", "Yi"]
                base = 1024.0
            else:
                prefixlist = ["", "K", "M", "G", "T", "P", "E", "Z", "Y"]
                base = 1000.0
            spacer_a = " "
            spacer_b = ""
        else:
            # Default to the prefixes of the International System of Units (SI)
            prefixlist = ["", "k", "M", "G", "T", "P", "E", "Z", "Y"]
            base = 1000.0
            spacer_a = ""
            spacer_b = " "

        if not magnitude:
            # calculate a suitable magnitude if not given
            while abs(response) >= base:
                mag += 1
                response /= base
        else:
            # utilize the given magnitude
            response /= base**magnitude

        if key == "Size":
            unit = "B"  # lock
        elif key == "Usage":
            unit = "Bh"  # arrow up
        elif key == "Cost":
            unit = "SEK"
            prefixlist[1] = "K"  # for currencies, the capital K is more common.
            prefixlist[3] = "B"  # for currencies, Billions are used instead of Giga

        if response > 0:
            # if magnitude was given, then use fixed number of digits
            # to allow for easier comparisons across projects
            if magnitude:
                return "{}{}{}".format(
                    f"{response:.2f}",
                    spacer_a,
                    prefixlist[magnitude] + spacer_b + unit,
                )
            else:  # if values are anyway prefixed individually, then strip trailing 0 for readability
                return "{}{}{}".format(
                    f"{response:.2f}".rstrip("0").rstrip("."),
                    spacer_a,
                    prefixlist[mag] + spacer_b + unit,
                )
        else:
            return f"0 {unit}"
    else:
        # Since table.add.row() expects a string, try to return whatever is not yet a string but also not numeric as string
        return str(response)


def get_token_header_contents(token):
    """Function to extract the jose header of the DDS token (JWE)

    :param token: a token that is not None

    returns the jose header of the token on successful deserialization"""
    try:
        token = jwt.JWT(jwt=token)
        return token.token.jose_header
    except (ValueError, InvalidJWEData, InvalidJWEOperation, InvalidJWSObject) as exc:
        raise dds_cli.exceptions.TokenDeserializationError(
            message="Token could not be deserialized."
        ) from exc


def get_token_expiration_time(token):
    """Function to extract the expiration time of the DDS token from its jose header.
    This expiration time is not the actual exp claim encrypted inside the token. This
    is only to help the cli know the time precisely instead of estimating.

    :param token: a token that is not None

    returns the exp claim for the cli from the jose header of the token"""

    jose_header = get_token_header_contents(token=token)
    if jose_header and "exp" in jose_header:
        return jose_header["exp"]
    raise dds_cli.exceptions.TokenExpirationMissingError(
        message="Expiration time could not be found in the header of the token."
    )


def readable_timedelta(duration):
    """Function to output a human-readable more sophisticated timedelta
    than str(datatime.timedelta) would.

    :param timedelta duration: difference in time, for example, token_exp_time - utcnow

    returns human-readable time representation from days down to the precision of minutes"""
    timespan = {}
    timespan["days"], rem = divmod(abs(duration.total_seconds()), 86_400)
    timespan["hours"], rem = divmod(rem, 3_600)
    timespan["minutes"], _ = divmod(rem, 60)
    time_parts = ((name, round(value)) for name, value in timespan.items())
    time_parts = [
        f"{value} {name if value > 1 else name[:-1]}" for name, value in time_parts if value > 0
    ]
    if time_parts:
        return " ".join(time_parts)
    else:
        return "less than a minute"


def get_deletion_confirmation(action: str, project: str) -> bool:
    """Confirm that the user wants to perform deletion."""
    question = f"Are you sure you want to {action} {project}? All its contents "
    if action in ["delete", "abort"]:
        question = question + "and metainfo "
    question += "will be deleted!"

    proceed_deletion = rich.prompt.Confirm.ask(question)
    return proceed_deletion


def print_or_page(item):
    """Paginate or print out depending on size of item."""
    if isinstance(item, rich.table.Table):
        if item.columns:
            if item.row_count + 5 > dds_cli.utils.console.height:
                with dds_cli.utils.console.pager():
                    dds_cli.utils.console.print(item)
            else:
                dds_cli.utils.console.print(item)
        else:
            raise dds_cli.exceptions.NoDataError("No users found.")
