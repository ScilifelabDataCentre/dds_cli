"""User module."""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import datetime
import getpass
import logging
import os
import pathlib
import stat
import subprocess

# Installed
from rich.prompt import Prompt

# Own modules
import dds_cli
from dds_cli import exceptions
from dds_cli.utils import get_token_expiration_time, readable_timedelta
import dds_cli.utils

###############################################################################
# START LOGGING CONFIG ################################# START LOGGING CONFIG #
###############################################################################

LOG = logging.getLogger(__name__)

###############################################################################
# CLASSES ########################################################### CLASSES #
###############################################################################


class User:
    """Represents a DDS user.

    when instantiating, an authentication token will be read from a file or
    renewed from the DDS API if the saved token is not found or has expired."""

    def __init__(
        self,
        force_renew_token: bool = False,
        no_prompt: bool = False,
        token_path: str = None,
        totp: str = None,
        allow_group: bool = False,
        authenticate_gui: bool = False,
        username_gui: str = None,
        password_gui: str = None,
    ):
        self.force_renew_token = force_renew_token
        self.no_prompt = no_prompt
        self.token = None
        self.token_path = token_path
        self.authenticate_gui = authenticate_gui
        self.username_gui = username_gui
        self.password_gui = password_gui

        # Fetch encrypted JWT token or authenticate against API
        self.__retrieve_token(totp=totp, allow_group=allow_group)

    @property
    def token_dict(self):
        """Get token as authorization dict for requests."""
        return {"Authorization": f"Bearer {self.token}"}

    # Private methods ######################### Private methods #
    def __retrieve_token(self, totp: str = None, allow_group: bool = False):
        """Fetch saved token from file otherwise authenticate user and saves the new token."""
        token_file = TokenFile(token_path=self.token_path, allow_group=allow_group)
        if not self.force_renew_token:
            LOG.debug("Retrieving token...")

            # Get token from file
            try:
                LOG.debug("Checking if token file exists.")
                self.token = token_file.read_token()
            except dds_cli.exceptions.TokenNotFoundError:
                self.token = None

        # Authenticate user and save token
        if not self.token:
            if self.authenticate_gui:
                self.token = self.__authenticate_user_gui()
            else:   
                if not self.force_renew_token:
                    LOG.info(
                    "No saved token found, or token has expired, proceeding with authentication"
                    )
                else:
                    LOG.info("Attempting to create the session token")
                self.token = self.__authenticate_user(totp=totp)
            token_file.save_token(self.token)

    def __authenticate_user_gui(self) -> tuple:

        response_json, _ = dds_cli.utils.perform_request(
            dds_cli.DDSEndpoint.ENCRYPTED_TOKEN,
            method="get",
            auth=(self.username_gui, self.password_gui),
            error_message="Failed to authenticate user",
        )
        print(response_json.get("token"))

        return response_json.get("token") #, response_json.get("secondfactor_method")

    def twofactor_gui(self, partial_auth_token: str, one_time_code: str):
        response_json, _ = dds_cli.utils.perform_request(
            dds_cli.DDSEndpoint.SECOND_FACTOR,
            method="get",
            headers={"Authorization": f"Bearer {partial_auth_token}"},
            json={"TOTP": one_time_code},
            error_message="Failed to authenticate with one-time authentication code",
        )
        return response_json

    def __authenticate_user(self, totp: str = None):
        """Authenticates the username and password via a call to the API."""
        LOG.debug("Starting authentication on the API...")

        if self.no_prompt:
            raise exceptions.AuthenticationError(
                message=(
                    "Authentication not possible when running with --no-prompt. "
                    "Please run the `dds auth login` command and authenticate interactively."
                )
            )
        
        username = Prompt.ask("DDS username")
        password = getpass.getpass(prompt="DDS password: ")

        if password == "":
            raise exceptions.AuthenticationError(
                message="Non-empty password needed to be able to authenticate."
            )

        try:
            response_json, _ = dds_cli.utils.perform_request(
                dds_cli.DDSEndpoint.ENCRYPTED_TOKEN,
                method="get",
                auth=(username, password),
                error_message="Failed to authenticate user",
            )
        except UnicodeEncodeError as exc:
            raise dds_cli.exceptions.ApiRequestError(
                message="The entered username or password seems to contain invalid characters. Please try again."
            ) from exc

        # Token received from API needs to be completed with a mfa timestamp
        partial_auth_token = response_json.get("token")
        secondfactor_method = response_json.get("secondfactor_method")


        totp_enabled = secondfactor_method == "TOTP"

        # Verify Second Factor
        if totp:
            if not totp_enabled:
                raise exceptions.AuthenticationError(
                    "Authentication failed, you have not yet activated one-time "
                    "authentication codes from authenticator app."
                )

            response_json, _ = dds_cli.utils.perform_request(
                dds_cli.DDSEndpoint.SECOND_FACTOR,
                method="get",
                headers={"Authorization": f"Bearer {partial_auth_token}"},
                json={"TOTP": totp},
                error_message="Failed to authenticate with one-time authentication code",
            )

        else:
            LOG.debug("2FA method: %s", "TOTP" if totp_enabled else "HOTP")
            if totp_enabled:
                LOG.info(
                    "Please enter the one-time authentication code from your authenticator app."
                )
                nr_digits = 6
            else:
                LOG.info(
                    "Please enter the one-time authentication code sent "
                    "to your email address (leave empty to exit):"
                )
                nr_digits = 8

            done = False
            while not done:
                entered_one_time_code = Prompt.ask("Authentication one-time code")
                if entered_one_time_code == "":
                    raise exceptions.AuthenticationError(
                        message="Exited due to no one-time authentication code entered."
                    )

                if not entered_one_time_code.isdigit():
                    LOG.info(
                        "Please enter a valid one-time code. It should consist of only digits."
                    )
                    continue
                if len(entered_one_time_code) != nr_digits:
                    LOG.info(
                        "Please enter a valid one-time code. It should consist of %s digits "
                        "(you entered %s digits).",
                        nr_digits,
                        len(entered_one_time_code),
                    )
                    continue

                if totp_enabled:
                    json_request = {"TOTP": entered_one_time_code}
                else:
                    json_request = {"HOTP": entered_one_time_code}

                response_json, _ = dds_cli.utils.perform_request(
                    dds_cli.DDSEndpoint.SECOND_FACTOR,
                    method="get",
                    headers={"Authorization": f"Bearer {partial_auth_token}"},
                    json=json_request,
                    error_message="Failed to authenticate with second factor",
                )

                # Step out of the while-loop
                done = True

        # Get token from response
        token = response_json.get("token")
        if not token:
            raise exceptions.AuthenticationError(
                message="Missing token in authentication response."
            )

        LOG.debug("User %s granted access to the DDS", username)

        return token

    @staticmethod
    def get_user_name_if_logged_in(token_path=None):
        """Returns a user name if logged in, otherwise None"""

        tokenfile = TokenFile(token_path=token_path)
        username = None
        if tokenfile.file_exists():
            token = tokenfile.read_token()
            if token and not tokenfile.token_expired(token=token):
                try:
                    response_json, _ = dds_cli.utils.perform_request(
                        dds_cli.DDSEndpoint.DISPLAY_USER_INFO,
                        method="get",
                        headers={"Authorization": f"Bearer {token}"},
                        error_message="Failed to get a username",
                    )
                    # Get response
                    username = response_json["info"]["username"]
                except:  # pylint: disable=bare-except
                    pass
        return username


class TokenFile:
    """A class to manage the saved token."""

    def __init__(self, token_path=None, allow_group: bool = False):
        # 600: -rw-------, 640: -rw-r-----, 660: -rw-rw----
        self.token_permission = 0o640 if allow_group else 0o600
        if token_path is None:
            self.token_file = dds_cli.TOKEN_FILE
        else:
            self.token_file = pathlib.Path(os.path.expanduser(token_path))

    def read_token(self):
        """Attempts to fetch a valid token from the token file.

        Returns None if no valid token can be found.

        Debug, not warning. Run prior to logging configured.
        """
        LOG.debug("Attempting to retrieve token from file...")

        if not self.file_exists():
            LOG.debug("Token file %s does not exist.", self.token_file)
            return None

        self.check_token_file_permissions()

        # Read token from file
        with self.token_file.open(mode="r") as file:  # pylint: disable=unspecified-encoding
            token = file.read()
            LOG.debug(type(token))
            if not token:
                raise exceptions.TokenNotFoundError(message="Token file is empty.")

        if self.token_expired(token=token):
            LOG.debug("The token has expired, reauthentication required.")
            return None

        LOG.debug("Token retrieved from file.")
        return token

    def file_exists(self):
        """Returns True if the token file exists."""
        return self.token_file.is_file()

    def save_token(self, token):
        """Saves the token to the token file."""

        if not self.token_file.is_file():
            self.token_file.touch(mode=self.token_permission)

        self.check_token_file_permissions()

        with self.token_file.open("w") as file:  # pylint: disable=unspecified-encoding
            file.write(token)

        if os.name == "nt":
            cli_username = os.environ.get("USERNAME")
            try:
                subprocess.check_call(
                    [
                        "icacls.exe",
                        str(self.token_file),
                        "/inheritance:r",
                        "/grant",
                        f"{cli_username}:(R,W)",
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except subprocess.CalledProcessError:
                LOG.error("Failed to set token file permissions")
        LOG.debug("New token saved to file.")

    def delete_token(self):
        """Deletes the token file."""

        if self.file_exists():
            self.token_file.unlink()

    def check_token_file_permissions(self):
        """Verify permissions for token file. Raises dds_cli.exceptions.DDSCLIException if
        permissions are not properly set.

        Returns None otherwise.
        """
        if os.name != "nt":
            st_mode = os.stat(self.token_file).st_mode
            permissions_octal = oct(stat.S_IMODE(st_mode))
            permissions_readable = stat.filemode(st_mode)
            if permissions_octal not in ["0o600", "0o640"]:
                raise exceptions.DDSCLIException(
                    message=(
                        f"Token file permissions are not properly set, (got {permissions_readable} "
                        f"instead of required '-rw-------'). Please remove {self.token_file} and rerun the command."
                    )
                )
        else:
            LOG.info(
                "Storing the login information locally - "
                "please ensure no one else an access the file at '%s'.",
                self.token_file,
            )

    def token_expired(self, token):
        """Check if the token has expired or is about to expire soon based on the UTC time.

        :param token: The DDS token that is obtained after successful basic and two-factor authentication.
            Token is already obtained before coming here, so not expected to be None.

        Returns True if the token has expired, False otherwise.
        """
        expiration_time = self.__token_dates(token=token)
        time_to_expire = expiration_time - datetime.datetime.utcnow()

        if expiration_time <= datetime.datetime.utcnow():
            LOG.debug("Token has expired. Now deleting it and fetching new token.")
            self.delete_token()
            return True

        if time_to_expire < dds_cli.TOKEN_EXPIRATION_WARNING_THRESHOLD:
            LOG.warning(
                "Saved token will expire in %s, "
                "please consider renewing the session using the 'dds auth login' command.",
                readable_timedelta(time_to_expire),
            )

        return False

    def token_report(self, token) -> str:
        """Produce report of token status.

        :param token: The DDS token that is obtained after successful basic and two-factor authentication.
            Token is already obtained before coming here, so not expected to be None.
        """

        expiration_time = self.__token_dates(token=token)
        time_to_expire = expiration_time - datetime.datetime.utcnow()
        expiration_message = f"Token will expire in {readable_timedelta(time_to_expire)}!"

        if expiration_time <= datetime.datetime.utcnow():
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

        return expiration_message ## RETURNS THE EXPIRATION MESSAGE FOR THE GUI
    
    # Private methods ############################################################ Private methods #
    def __token_dates(self, token):  # pylint: disable=inconsistent-return-statements
        """Returns the expiration time in UTC that is extracted from the token jose header."""

        expiration_time = get_token_expiration_time(token=token)

        if expiration_time:
            return datetime.datetime.fromisoformat(expiration_time)
