"""Data Delivery System saved authentication token manager."""
import logging

# Own modules
from dds_cli import base
from dds_cli import user

###############################################################################
# START LOGGING CONFIG ################################# START LOGGING CONFIG #
###############################################################################

LOG = logging.getLogger(__name__)


###############################################################################
# CLASSES ########################################################### CLASSES #
###############################################################################


class Auth(base.DDSBaseClass):
    """Authentication manager class."""

    def __init__(
        self,
        username: str,
        authenticate: bool = True,
    ):
        """Handle actions regarding session management in DDS."""
        # Initiate DDSBaseClass to authenticate user
        super().__init__(
            username=username,
            authenticate=authenticate,
            method_check=False,
            force_renew_token=True,  # Only used if authenticate is True
        )

    def check(self):
        token_file = user.TokenFile()
        if token_file.file_exists():
            token_file.check_token_file_permissions()
            token = token_file.read_token()
            token_file.token_report(token=token)
        else:
            LOG.error(f"[red]No saved authentication token found![/red]")

    def logout(self):
        token_file = user.TokenFile()
        if token_file.file_exists():
            token_file.delete_token()
        else:
            LOG.info(f"[green]Already logged out![/green]")
