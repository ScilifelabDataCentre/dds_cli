"""User module."""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import datetime
import logging
import os
import stat
import getpass
import requests
import simplejson

# Installed
import rich

# Own modules
import dds_cli
from dds_cli import exceptions

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

    def __init__(self, username: str, force_renew_token: bool = False, no_prompt: bool = False):
        self.username = username
        self.force_renew_token = force_renew_token
        self.no_prompt = no_prompt
        self.token = None

        # Fetch encrypted JWT token or authenticate against API
        self.__retrieve_token()

    @property
    def token_dict(self):
        return {"Authorization": f"Bearer {self.token}"}

    # Private methods ######################### Private methods #
    def __retrieve_token(self):
        """Attempts to fetch saved token from file otherwise authenticate user and saves the new token."""

        token_file = TokenFile()

        if not self.force_renew_token:
            LOG.debug(f"Retrieving token for user {self.username}")

            # Get token from file
            try:
                LOG.debug(f"Checking if token file exists for user {self.username}")
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
                LOG.info("Attempting to renew the session token")
            self.token = self.__authenticate_user()
            token_file.save_token(self.token)

    def __authenticate_user(self):
        """Authenticates the username and password via a call to the API."""

        LOG.debug(f"Authenticating the user: {self.username} on the api")

        if self.no_prompt:
            raise exceptions.AuthenticationError(
                message=(
                    "Authentication not possible when running with --no-prompt. "
                    "Please run the `dds auth login` command and authenticate interactively."
                )
            )
        if self.username is None:
            self.username = rich.prompt.Prompt.ask("DDS username")

        password = getpass.getpass(prompt="DDS password: ")

        if password == "":
            raise exceptions.AuthenticationError(
                message="Non-empty password needed to be able to authenticate."
            )

        try:
            response = requests.get(
                dds_cli.DDSEndpoint.ENCRYPTED_TOKEN,
                auth=(self.username, password),
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
            else:
                raise dds_cli.exceptions.ApiResponseError(
                    message=f"API returned an error: {response_json.get('message', 'Unknown Error!')}"
                )

        # Token received from API needs to be completed with a mfa timestamp
        partial_auth_token = response_json.get("token")

        # Verify 2fa email token
        LOG.info(
            "Please enter the one-time authentication code sent to your email address (leave empty to exit):"
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
                    f"Please enter a valid one-time code. It should consist of 8 digits (you entered {len(entered_one_time_code)} digits)."
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

        LOG.debug(f"User {self.username} granted access to the DDS")

        return token


class TokenFile:
    """A class to manage the saved token."""

    def __init__(self):
        self.token_file = dds_cli.TOKEN_FILE

    def read_token(self):
        """Attempts to fetch a valid token from the token file.

        Returns None if no valid token can be found."""

        if not self.file_exists():
            LOG.debug(f"Token file {self.token_file} does not exist.")
            return None

        self.check_token_file_permissions()

        if self.token_expired():
            LOG.debug("No token retrieved from file, will fetch new token from api")
            return None

        # Read token from file
        with self.token_file.open() as file:
            token = file.read()
            if not token:
                raise exceptions.TokenNotFoundError(message="Token file is empty.")

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
        st_mode = os.stat(self.token_file).st_mode
        permissions_octal = oct(stat.S_IMODE(st_mode))
        permissions_readable = stat.filemode(st_mode)
        if permissions_octal != "0o600":
            raise exceptions.DDSCLIException(
                message=f"Token file permissions are not properly set, (got {permissions_readable} instead of required '-rw-------'). Please remove {self.token_file} and rerun the command."
            )

    def token_expired(self):
        """Check how old the token is based on the modification time of the token file.

        It compares the age with the dds variables TOKEN_MAX_AGE and TOKEN_WARNING_AGE to decide
        what to do.

        Returns True if the token has expired, False otherwise.

        ** Notice, this does not actually know the expiration time of the token, it's possible that the
        expiration time has changed upstream in which case the variables need to be updated.

        if check is True, token age will be reported to stdout
        """
        age, expiration_time = self.__token_dates()
        LOG.debug(f"Token file age: {age}")
        if age > dds_cli.TOKEN_MAX_AGE:
            LOG.debug(
                "Token file is too old so token has likely expired. Now deleting it and fetching new token."
            )
            self.delete_token()
            return True
        elif age > dds_cli.TOKEN_WARNING_AGE:
            LOG.warning(
                f"Saved token will soon expire: {expiration_time.strftime('%Y-%m-%d %H:%M:%S')}, please consider renewing the session using the 'dds auth login' command."
            )

        return False

    def token_report(self):
        """Produce report of token status."""
        age, expiration_time = self.__token_dates()

        age_hours, rem = divmod(age.seconds, 3600)
        age_minutes, _ = divmod(rem, 60)
        expiration_time = expiration_time.strftime("%Y-%m-%d %H:%M:%S")

        if age > dds_cli.TOKEN_MAX_AGE:
            markup_color = "red"
            sign = ":no_entry_sign:"
            message = "Token has expired!"
        elif age > dds_cli.TOKEN_WARNING_AGE:
            markup_color = "yellow"
            sign = ":warning-emoji:"
            message = "Token will expire soon!"
        else:
            markup_color = "green"
            sign = ":white_check_mark:"
            message = "Token is OK!"

        # Heading
        LOG.info(f"[{markup_color}]{sign}  {message} {sign} [/{markup_color}]")
        if age.days > 0:
            LOG.info(
                f"[{markup_color}]Token age: {age.days} days {age_hours} hours[/{markup_color}]"
            )
        else:
            LOG.info(
                f"[{markup_color}]Token age: {age_hours} hours {age_minutes} minutes[/{markup_color}]"
            )

        if age > dds_cli.TOKEN_MAX_AGE:
            LOG.info(f"[{markup_color}]Token expired: {expiration_time}[/{markup_color}]")
        else:
            LOG.info(f"[{markup_color}]Token expires: {expiration_time}[/{markup_color}]")

    # Private methods ############################################################ Private methods #
    def __token_dates(self):
        # os.path.getmtime() gets modified time of token file from local, so already localized
        modification_time = datetime.datetime.fromtimestamp(os.path.getmtime(self.token_file))
        age = datetime.datetime.now() - modification_time
        expiration_time = modification_time + dds_cli.TOKEN_MAX_AGE

        return age, expiration_time
