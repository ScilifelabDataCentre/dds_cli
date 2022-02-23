"""DDS CLI utils module."""

import numbers

import rich.console
import simplejson
from jwcrypto.common import InvalidJWEOperation
from jwcrypto.jwe import InvalidJWEData
from jwcrypto.jws import InvalidJWSObject
from jwcrypto import jwt

import dds_cli.exceptions

console = rich.console.Console()
stderr_console = rich.console.Console(stderr=True)


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

    if isinstance(response, numbers.Number):
        response = float("{:.3g}".format(response))
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
            spacerA = " "
            spacerB = ""
        else:
            # Default to the prefixes of the International System of Units (SI)
            prefixlist = ["", "k", "M", "G", "T", "P", "E", "Z", "Y"]
            base = 1000.0
            spacerA = ""
            spacerB = " "

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
                    "{:.2f}".format(response),
                    spacerA,
                    prefixlist[magnitude] + spacerB + unit,
                )
            else:  # if values are anyway prefixed individually, then strip trailing 0 for readability
                return "{}{}{}".format(
                    "{:.2f}".format(response).rstrip("0").rstrip("."),
                    spacerA,
                    prefixlist[mag] + spacerB + unit,
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
    except (ValueError, InvalidJWEData, InvalidJWEOperation, InvalidJWSObject):
        raise dds_cli.exceptions.TokenDeserializationError(
            message="Token could not be deserialized."
        )


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
