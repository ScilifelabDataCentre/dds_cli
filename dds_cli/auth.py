"""Data Delivery System authentication manager."""

# Standard library
import logging
import getpass
from datetime import datetime
from typing import Optional

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
    ):
        """Handle actions regarding session management in DDS."""
        # Initiate DDSBaseClass to authenticate user
        # Will authenticate user automatically if authenticate is True,
        # else need to call login and confirm_twofactor methods to authenticate user
        # This is to be able to use the auth class in the GUI code,
        # where the user is not prompted for username and password
        super().__init__(
            authenticate=authenticate,
            force_renew_token=force_renew_token,
            token_path=token_path,
            totp=totp,
            allow_group=allow_group,
        )

        # Initialize user class for calling login and confirm_twofactor methods to authenticate user
        self.user = user.User(
            force_renew_token=force_renew_token,
            token_path=token_path,
            allow_group=allow_group,
        )

    def login(self, username: Optional[str] = None, password: Optional[str] = None) -> tuple:
        """Login user to DDS. Used to manually authenticate users with username and password.
        If not provided, will prompt for them.

        :param username: The username to login with.
        :param password: The password to login with.

        :return: Partial auth token and second factor method
        """
        return self.user.login(username, password)

    def confirm_twofactor(
        self,
        partial_auth_token: str,
        secondfactor_method: str,
        totp: str = None,
        twofactor_code: Optional[str] = None,
    ):
        """Confirm 2FA for user. Used to manually confirm the 2FA code.
        If not provided, will prompt for it.

        :param partial_auth_token: The partial auth token.
        :param twofactor_code: The 2FA code to confirm.

        """
        self.user.confirm_twofactor(partial_auth_token, secondfactor_method, totp, twofactor_code)
        self.token = self.user.token_dict

    def check(self) -> Optional[datetime]:
        """Check if token exists and returns the token expiration time.

        :return: Token info if token exists, None otherwise.
        """
        token_file = user.TokenFile(token_path=self.token_path)
        if token_file.file_exists():
            token = token_file.read_token()
            if token:
                return token_file.token_report(token=token)
        return None

    def logout(self) -> bool:
        """Logout user by removing authenticated token.

        :return: True if logout was successful, False if already logged out.
        """
        token_file = user.TokenFile(token_path=self.token_path)
        if token_file.file_exists():
            token_file.delete_token()
            return True
        return False

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
