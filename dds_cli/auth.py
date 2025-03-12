"""Data Delivery System authentication manager."""

# Standard library
import logging
import getpass
from re import S

# Installed
from rich.prompt import Prompt

# Own modules
import dds_cli
from dds_cli import base
from dds_cli import exceptions
from dds_cli import user
import dds_cli.utils

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
        force_renew_token: bool = True,  # Only used if authenticate is True
        token_path: str = None,
        totp: str = None,
        allow_group: bool = False,
        authenticate_gui: bool = False,
        username_gui: str = None,
        password_gui: str = None,
    ):
        """Handle actions regarding session management in DDS."""
        # Initiate DDSBaseClass to authenticate user
        super().__init__(
            authenticate=authenticate,
            method_check=False,
            force_renew_token=force_renew_token,
            token_path=token_path,
            totp=totp,
            allow_group=allow_group,
            authenticate_gui=authenticate_gui,
            username_gui=username_gui,
            password_gui=password_gui,
        )

    def check(self) -> str:
        """Check if token exists and return info."""
        token_file = user.TokenFile(token_path=self.token_path)
        if token_file.file_exists():
            token = token_file.read_token()
            if token:
                return token_file.token_report(token=token)
        else:
            LOG.info(
                "[red]No saved token found, or token has expired. "
                "Authenticate yourself with `dds auth login` to use this functionality![/red]"
            )

    def logout(self):
        """Logout user by removing authenticated token."""
        token_file = user.TokenFile(token_path=self.token_path)
        if token_file.file_exists():
            token_file.delete_token()
            LOG.info("[green] :white_check_mark: Successfully logged out![/green]")
        else:
            LOG.info("[green]Already logged out![/green]")

    def twofactor(self, auth_method: str = None):
        """Perform 2FA for user."""
        if auth_method == "totp":
            response_json, _ = dds_cli.utils.perform_request(
                endpoint=dds_cli.DDSEndpoint.USER_ACTIVATE_TOTP,
                headers=self.token,
                method="post",
            )
        else:
            # Need to authenticate again since TOTP might have been lost
            LOG.info(
                "Activating authentication via email, please (re-)enter your username and password:"
            )
            username: str = Prompt.ask("DDS username")
            password: str = getpass.getpass(prompt="DDS password: ")

            if password == "":
                raise exceptions.AuthenticationError(
                    message="Non-empty password needed to be able to authenticate."
                )

            response_json, _ = dds_cli.utils.perform_request(
                endpoint=dds_cli.DDSEndpoint.USER_ACTIVATE_HOTP,
                method="post",
                auth=(username, password),
            )

        LOG.info(response_json.get("message"))

    def deactivate(self, username: str = None):
        """Deactivate TOTP for user."""
        response_json, _ = dds_cli.utils.perform_request(
            endpoint=dds_cli.DDSEndpoint.TOTP_DEACTIVATE,
            headers=self.token,
            json={"username": username},
            method="put",
        )
        LOG.info(response_json.get("message"))
