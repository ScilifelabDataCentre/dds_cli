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
import requests
import simplejson
import stat
import subprocess

# Installed
import rich

# Own modules
import dds_cli
from dds_cli import exceptions
from dds_cli.utils import get_token_expiration_time, readable_timedelta

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
    ):
        self.force_renew_token = force_renew_token
        self.no_prompt = no_prompt
        self.token = None
        self.token_path = token_path

        # Fetch encrypted JWT token or authenticate against API
        self.__retrieve_token()

    @property
    def token_dict(self):
        """Get token as authorization dict for requests."""
        return {"Authorization": f"Bearer {self.token}"}

    # Private methods ######################### Private methods #
    def __retrieve_token(self):
        """Fetch saved token from file otherwise authenticate user and saves the new token."""
        token_file = TokenFile(token_path=self.token_path)

        if not self.force_renew_token:
            LOG.debug("Retrieving token.")

            # Get token from file
            try:
                LOG.debug("Checking if token file exists.")
                self.token = token_file.read_token()
            except dds_cli.exceptions.TokenNotFoundError:
                self.token = None

        # Authenticate user and save token
        if not self.token:
            if not self.force_renew_token:
                LOG.info(
                    "No saved token found, or token has expired, proceeding with authentication"
                )
            else:
                LOG.info("Attempting to create the session token")
            self.token = self.__authenticate_user()
            token_file.save_token(self.token)

    def __authenticate_user(self):
        """Authenticates the username and password via a call to the API."""
        LOG.debug("Starting authentication on the API.")

        if self.no_prompt:
            raise exceptions.AuthenticationError(
                message=(
                    "Authentication not possible when running with --no-prompt. "
                    "Please run the `dds auth login` command and authenticate interactively."
                )
            )

        username = rich.prompt.Prompt.ask("DDS username")
        password = getpass.getpass(prompt="DDS password: ")

        if password == "":
            raise exceptions.AuthenticationError(
                message="Non-empty password needed to be able to authenticate."
            )

        try:
            response = requests.get(
                dds_cli.DDSEndpoint.ENCRYPTED_TOKEN,
                auth=(username, password),
                timeout=dds_cli.DDSEndpoint.TIMEOUT,
            )
            response_json = response.json()
        except requests.exceptions.RequestException as err:
            raise exceptions.ApiRequestError(message=str(err)) from err
        except simplejson.JSONDecodeError as err:
            raise dds_cli.exceptions.ApiResponseError(message=str(err))

        if not response.ok:
            if response.status_code == 401:
                raise exceptions.AuthenticationError(
                    "Authentication failed, incorrect username and/or password."
                )

            raise dds_cli.exceptions.ApiResponseError(
                message=f"API returned an error: {response_json.get('message', 'Unknown Error!')}"
            )

        # Token received from API needs to be completed with a mfa timestamp
        partial_auth_token = response_json.get("token")

        # Verify 2fa email token
        LOG.info(
            "Please enter the one-time authentication code sent "
            "to your email address (leave empty to exit):"
        )
        done = False
        while not done:
            entered_one_time_code = rich.prompt.Prompt.ask("Authentication one-time code")
            if entered_one_time_code == "":
                raise exceptions.AuthenticationError(
                    message="Exited due to no one-time authentication code entered."
                )

            if not entered_one_time_code.isdigit():
                LOG.info("Please enter a valid one-time code. It should consist of only digits.")
                continue
            if len(entered_one_time_code) != 8:
                LOG.info(
                    "Please enter a valid one-time code. It should consist of 8 digits "
                    f"(you entered {len(entered_one_time_code)} digits)."
                )
                continue

            try:
                response = requests.get(
                    dds_cli.DDSEndpoint.SECOND_FACTOR,
                    headers={"Authorization": f"Bearer {partial_auth_token}"},
                    json={"HOTP": entered_one_time_code},
                    timeout=dds_cli.DDSEndpoint.TIMEOUT,
                )
                response_json = response.json()
            except requests.exceptions.RequestException as err:
                raise exceptions.ApiRequestError(message=str(err)) from err

            if response.ok:
                # Step out of the while-loop
                done = True
            if not response.ok:
                message = response_json.get("message", "Unexpected error!")
                if response.status_code == 401:
                    try_again = rich.prompt.Confirm.ask(
                        "Second factor authentication failed, would you like to try again?"
                    )
                    if not try_again:
                        raise exceptions.AuthenticationError(message="Exited due to user choice.")
                else:
                    raise exceptions.ApiResponseError(message=message)

        # Get token from response
        token = response_json.get("token")
        if not token:
            raise exceptions.AuthenticationError(
                message="Missing token in authentication response."
            )

        LOG.debug(f"User {username} granted access to the DDS")

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
                    response = requests.get(
                        dds_cli.DDSEndpoint.DISPLAY_USER_INFO,
                        headers={"Authorization": f"Bearer {token}"},
                        timeout=dds_cli.DDSEndpoint.TIMEOUT,
                    )
                    # Get response
                    response_json = response.json()
                    username = response_json["info"]["username"]
                except:
                    pass
        return username


class TokenFile:
    """A class to manage the saved token."""

    def __init__(self, token_path=None):
        if token_path is None:
            self.token_file = dds_cli.TOKEN_FILE
        else:
            self.token_file = pathlib.Path(os.path.expanduser(token_path))

    def read_token(self):
        """Attempts to fetch a valid token from the token file.

        Returns None if no valid token can be found."""

        if not self.file_exists():
            LOG.debug(f"Token file {self.token_file} does not exist.")
            return None

        self.check_token_file_permissions()

        # Read token from file
        with self.token_file.open(mode="r") as file:
            token = file.read()
            if not token:
                raise exceptions.TokenNotFoundError(message="Token file is empty.")

        if self.token_expired(token=token):
            LOG.debug("No token retrieved from file, will fetch new token from API")
            return None

        LOG.debug("Token retrieved from file.")
        return token

    def file_exists(self):
        """Returns True if the token file exists."""
        return self.token_file.is_file()

    def save_token(self, token):
        """Saves the token to the token file."""

        if not self.token_file.is_file():
            self.token_file.touch(mode=0o600)

        self.check_token_file_permissions()

        with self.token_file.open("w") as file:
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
            except subprocess.CalledProcessError as exc:
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
            if permissions_octal != "0o600":
                raise exceptions.DDSCLIException(
                    message=f"Token file permissions are not properly set, (got {permissions_readable} instead of required '-rw-------'). Please remove {self.token_file} and rerun the command."
                )
        else:
            LOG.info("Unable to confirm whether file permissions are correct on Windows.")

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
        elif time_to_expire < dds_cli.TOKEN_EXPIRATION_WARNING_THRESHOLD:
            LOG.warning(
                f"Saved token will expire in {readable_timedelta(time_to_expire)}, "
                f"please consider renewing the session using the 'dds auth login' command."
            )

        return False

    def token_report(self, token):
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
            LOG.info(f"[{markup_color}]{sign}  {message} {sign} [/{markup_color}]")
        LOG.info(f"[{markup_color}]{sign}  {expiration_message} {sign} [/{markup_color}]")

    # Private methods ############################################################ Private methods #
    def __token_dates(self, token):
        """Returns the expiration time in UTC that is extracted from the token jose header."""

        expiration_time = get_token_expiration_time(token=token)

        if expiration_time:
            return datetime.datetime.fromisoformat(expiration_time)
