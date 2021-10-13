"""Custom click option classes - handles combinations of required options."""

# IMPORTS ################################################################################ IMPORTS #

# Standard library

# Installed
import click

# Own modules


# CLASSES ################################################################################ CLASSES #
class RequiredIf(click.Option):
    """Custom click Option class. Option required if other option has specific value."""

    def __init__(self, *args, **kwargs):
        """Check option use, adds help text and initiates parent class."""
        self.required_if = kwargs.pop("required_if")
        self.required_value = kwargs.pop("required_value")
        assert self.required_if, "'required_if' parameter required"
        assert self.required_value, "'required_value' parameter required"

        kwargs["help"] = (
            kwargs.get("help", "") + f"This argument is required if {self.required_if} is specified"
        ).strip()
        super(RequiredIf, self).__init__(*args, **kwargs)

    def handle_parse_result(self, ctx, opts, args):
        """Check that option is used if other option has value. Raises UsageError."""
        # required option value present
        required_option_present = opts.get(self.required_if) == self.required_value

        if required_option_present:
            if not self.name in opts:
                raise click.UsageError(
                    f"Illegal usage: '{self.name}'  is required if "
                    f"'{self.required_if}' is specified."
                )

        return super(RequiredIf, self).handle_parse_result(ctx, opts, args)
