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
        check: bool = False,
    ):
        """Handle actions regarding session management in DDS."""
        # Initiate DDSBaseClass to authenticate user
        super().__init__(
            username=username,
            authenticate=not check,
            method_check=False,
            force_renew_token=True,  # Only used if authenticate is True
        )

    def check(self):
        token_file = user.TokenFile()
        token_file.check_token_file_permissions()
        token_file.token_report()
