import rich.console
import numbers

console = rich.console.Console(stderr=True)


def format_api_response(response, key, magnitude=None, iec_standard=False):
    """Takes a value e.g. bytes and reformats it to include a unit prefix"""
    if isinstance(response, str):
        return response  # pass the response if already a string

    if isinstance(response, numbers.Number):
        response = float("{:.3g}".format(response))
        mag = 0

        if key in ["Size", "Usage"]:
            if iec_standard:
                # The IEC created prefixes such as kibi, mebi, gibi, etc., to unambiguously denote powers of 1024
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
            response /= base * magnitude
            mag = magnitude

        if key == "Size":
            unit = "B"  # lock
        elif key == "Usage":
            unit = "Bh"  # arrow up
        elif key == "Cost":
            unit = "SEK"
            prefixlist[1] = "K"  # for currencies, the capital K is more common.

        if response > 0:
            return "{}{}{}".format(
                "{:.3g}".format(response).rstrip("0").rstrip("."),
                spacerA,
                prefixlist[mag] + spacerB + unit,
            )
        else:
            return f"0 {unit}"
    else:
        # Since table.add.row() expects a string, try to return whatever is not yet a string but also not numeric as string
        return str(response)
