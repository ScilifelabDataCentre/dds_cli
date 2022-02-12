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
import pytz
import requests
import simplejson
import tzlocal

# Installed
import rich

# Own modules
import dds_cli
from dds_cli import exceptions
from dds_cli.utils import get_token_header_contents, readable_timedelta

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
                self.token, _ = token_file.read_token()
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
            return None, None

        self.check_token_file_permissions()

        # Read token from file
        with self.token_file.open() as file:
            token = file.read()
            if not token:
                raise exceptions.TokenNotFoundError(message="Token file is empty.")

            # Use lifetime from token header if given, else read default from config
        try:
            token_metadata = get_token_header_contents(token)
        except exceptions.TokenNotFoundError:
            token_metadata = None

        if self.token_expired(token_metadata=token_metadata):
            LOG.debug("No token retrieved from file, will fetch new token from API")
            return None, None

        LOG.debug("Token retrieved from file.")
        return token, token_metadata

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

    def token_expired(self, token_metadata=None):
        """Check how old the token is based on the modification time of the token file.

        It compares the age with the dds variables TOKEN_MAX_AGE and TOKEN_WARNING_AGE to decide
        what to do.

        Returns True if the token has expired, False otherwise.
        """
        token_dates = self.__token_dates(token_metadata=token_metadata)

        LOG.debug(f"Token file age: {readable_timedelta(token_dates['age'])}")
        if token_dates["lft"].total_seconds() >= 0:
            LOG.debug("Token has expired. Now deleting it and fetching new token.")
            self.delete_token()
            return True
        elif dds_cli.TOKEN_WARNING_AGE * dds_cli.TOKEN_MAX_AGE <= token_dates["age"]:
            LOG.warning(
                f"Saved token will expire in {readable_timedelta(token_dates['lft'])}, please consider renewing the session using the 'dds auth login' command."
            )

        return False

    def token_report(self, token_metadata=None):
        """Produce report of token status."""

        if token_metadata:
            consignee = token_metadata.get("csg", None)

        token_dates = self.__token_dates(token_metadata=token_metadata)
        age = token_dates["age"]
        lifetime = token_dates["lft"]
        expiration_time = token_dates["exp"]
        # display expiration time in local time
        expiration_time = expiration_time.astimezone(tz=tzlocal.get_localzone()).strftime(
            "on %d %B %Y at %H:%Mh"
        )

        if lifetime.total_seconds() >= 0:
            markup_color = "red"
            sign = ":no_entry_sign:"
            message = "Token has expired!"
        elif dds_cli.TOKEN_WARNING_AGE * dds_cli.TOKEN_MAX_AGE <= age:
            markup_color = "yellow"
            sign = ":warning-emoji:"
            message = "Token will expire soon!"
        else:
            markup_color = "green"
            sign = ":white_check_mark:"
            message = "Token is OK!"

        # Heading
        LOG.info(f"[{markup_color}]{sign}  {message} {sign} [/{markup_color}]")
        LOG.info(f"[{markup_color}]Token age: {readable_timedelta(age)}[/{markup_color}]")

        if lifetime.total_seconds() < 0:
            LOG.info(
                f"[{markup_color}]Token expires: {expiration_time} (in {readable_timedelta(lifetime)})[/{markup_color}]"
            )
        else:
            LOG.info(f"[{markup_color}]Token expired: {expiration_time}[/{markup_color}]")

        if consignee:
            LOG.info(f"[{markup_color}]Token issued to: {consignee}[/{markup_color}]")

    # Private methods ############################################################ Private methods #
    def __token_dates(self, token_metadata):
        """Returns definitive or estimated values for the issue date, token's age, lifetime and expiration time in UTC."""

        local_tz = tzlocal.get_localzone()
        utc_tz = pytz.timezone("UTC")

        # Try to use the Issued At Claim (iat), otherwise fall back to modification_time of the file
        if token_metadata and token_metadata.get("iat", None):
            issued_at = datetime.datetime.fromtimestamp(token_metadata.get("iat"), tz=utc_tz)
        else:
            issued_at = datetime.datetime.fromtimestamp(
                os.path.getmtime(self.token_file), tz=local_tz
            )

        age = datetime.datetime.utcnow().replace(tzinfo=utc_tz) - issued_at

        # Try to use the Expiration Time (exp), otherwise fall back to calculation based on configured lifetime value
        if token_metadata and token_metadata.get("exp", None):
            expiration_time = datetime.datetime.fromtimestamp(token_metadata.get("exp"), tz=utc_tz)
        else:
            expiration_time = issued_at + dds_cli.TOKEN_MAX_AGE

        # lifetime is returned as a negative value / countdown
        lifetime = datetime.datetime.utcnow().replace(tzinfo=utc_tz) - expiration_time

        return {"iat": issued_at, "age": age, "lft": lifetime, "exp": expiration_time}
