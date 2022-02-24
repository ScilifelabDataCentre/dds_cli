"""Data Delivery System saved authentication token manager."""
import logging
import requests
import simplejson

# Own modules
import dds_cli
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
        force_renew_token: bool = True,
        totp: str = None,
    ):
        """Handle actions regarding session management in DDS."""
        # Initiate DDSBaseClass to authenticate user
        super().__init__(
            username=username,
            authenticate=authenticate,
            method_check=False,
            force_renew_token=force_renew_token,  # Only used if authenticate is True
            totp=totp,  # Only used if authenticate is True
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

    def twofactor(self, totp):
        if totp:
            try:
                response = requests.post(
                    dds_cli.DDSEndpoint.USER_ACTIVATE_TOTP,
                    headers=self.token,
                )
                response_json = response.json()
            except requests.exceptions.RequestException as err:
                raise dds_cli.exceptions.ApiRequestError(message=str(err))
            except simplejson.JSONDecodeError as err:
                raise dds_cli.exceptions.ApiResponseError(message=str(err))

            if not response.ok:
                raise dds_cli.exceptions.ApiResponseError(message=response.reason)

            LOG.info(response_json.get("message"))
