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
        authenticate: bool = True,
        token_path: str = None,
    ):
        """Handle actions regarding session management in DDS."""
        # Initiate DDSBaseClass to authenticate user
        super().__init__(
            authenticate=authenticate,
            method_check=False,
            force_renew_token=True,  # Only used if authenticate is True
            token_path=token_path,
        )

    def check(self):
        token_file = user.TokenFile(token_path=self.token_path)
        if token_file.file_exists():
            token = token_file.read_token()
            token_file.token_report(token=token)
        else:
            LOG.info(
                "[red]No saved token found, or token has expired. Authenticate yourself with `dds auth login` to use this functionality.![/red]"
            )

    def logout(self):
        token_file = user.TokenFile(token_path=self.token_path)
        if token_file.file_exists():
            token_file.delete_token()
            LOG.info("[green] :white_check_mark: Successfully logged out![/green]")
        else:
            LOG.info("[green]Already logged out![/green]")
