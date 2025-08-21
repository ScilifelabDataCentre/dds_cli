"""Message helper module"""

from datetime import datetime
import logging

import dds_cli
from dds_cli.utils import readable_timedelta

###############################################################################
# START LOGGING CONFIG ################################# START LOGGING CONFIG #
###############################################################################

LOG = logging.getLogger(__name__)

###############################################################################
# CLASSES ########################################################### CLASSES #
###############################################################################


class CLIMessageHelper:
    """Helper class for generating messages for the CLI."""

    def __init__(self):
        pass

    # Logout messages ########################################################## Logout messages #

    def logout_message(self, logout_ok: bool):
        """Log logout message.

        :param logout_ok: The status of the logout action.
        True if logout was successful, False if already logged out.
        """
        if logout_ok:
            LOG.info("[green] :white_check_mark: Successfully logged out![/green]")
        else:
            LOG.info("[orange]Already logged out![/orange]")

    # Token messages ############################################################ Token messages #

    def token_expired_message(self):
        """Log token expiration message."""
        LOG.info(
            "[red]No saved token found, or token has expired. "
            "Authenticate yourself with `dds auth login` to use this functionality![/red]"
        )

    def token_report_message(self, expiration_time: datetime):
        """Log token status report.

        :param expiration_time: The expiration time of the token.
        """

        time_to_expire = expiration_time - datetime.utcnow()
        expiration_message = f"Token will expire in {readable_timedelta(time_to_expire)}!"

        if expiration_time <= datetime.utcnow():
            markup_color = "red"
            sign = ":no_entry_sign:"
            message = "Token has expired!"
        elif time_to_expire < dds_cli.TOKEN_EXPIRATION_WARNING_THRESHOLD:
            markup_color = "yellow"
            sign = ":warning-emoji:"
            message = ""
        else:
            markup_color = "green"
            sign = ":white_check_mark:"
            message = "Token is OK!"

        if message:
            LOG.info("[%s]%s  %s %s [/%s]", markup_color, sign, message, sign, markup_color)
        LOG.info("[%s]%s  %s %s [/%s]", markup_color, sign, expiration_message, sign, markup_color)
