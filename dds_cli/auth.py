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
        authenticate: bool = True,
        force_renew_token: bool = True,  # Only used if authenticate is True
        token_path: str = None,
        totp: str = None,
    ):
        """Handle actions regarding session management in DDS."""
        # Initiate DDSBaseClass to authenticate user
        super().__init__(
            authenticate=authenticate,
            method_check=False,
            force_renew_token=force_renew_token,
            token_path=token_path,
            totp=totp,
        )

    def check(self):
        token_file = user.TokenFile(token_path=self.token_path)
        if token_file.file_exists():
            token = token_file.read_token()
            token_file.token_report(token=token)
        else:
            LOG.info(
                "[red]No saved token found, or token has expired. Authenticate yourself with `dds auth login` to use this functionality![/red]"
            )

    def logout(self):
        token_file = user.TokenFile(token_path=self.token_path)
        if token_file.file_exists():
            token_file.delete_token()
            LOG.info("[green] :white_check_mark: Successfully logged out![/green]")
        else:
            LOG.info("[green]Already logged out![/green]")

    def twofactor(self, auth_method: str = None):
        if auth_method == "totp":
            try:
                response = requests.put(
                    dds_cli.DDSEndpoint.USER_ACTIVATE_TOTP,
                    headers=self.token,
                    json={"activate_totp": True},
                )
                response_json = response.json()
            except requests.exceptions.RequestException as err:
                raise dds_cli.exceptions.ApiRequestError(message=str(err))
            except simplejson.JSONDecodeError as err:
                raise dds_cli.exceptions.ApiResponseError(message=str(err))

            if not response.ok:
                raise dds_cli.exceptions.ApiResponseError(message=response.reason)

            LOG.info(response_json.get("message"))
        elif auth_method == "hotp":
            raise dds_cli.exceptions.DDSCLIException(message="Not implemented yet!")
