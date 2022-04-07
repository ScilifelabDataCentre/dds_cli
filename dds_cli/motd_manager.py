"""Motd Manager module."""

####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
###################################################################################################

# Standard library
import logging

# Installed
import http
import requests
import rich.markup
from rich.table import Table
import simplejson

# Own modules
import dds_cli
import dds_cli.auth
import dds_cli.base
import dds_cli.exceptions
import dds_cli.utils

# from dds_cli import exceptions
from dds_cli import DDSEndpoint


####################################################################################################
# START LOGGING CONFIG ###################################################### START LOGGING CONFIG #
####################################################################################################

LOG = logging.getLogger(__name__)


####################################################################################################
# CLASSES ################################################################################ CLASSES #
####################################################################################################


class MotdManager(dds_cli.base.DDSBaseClass):
    """Admin class for managing motd."""

    def __init__(
        self,
        authenticate: bool = True,
        method: str = "add",
        no_prompt: bool = False,
        token_path: str = None,
    ):
        """Initialize, incl. user authentication."""
        # Initiate DDSBaseClass to authenticate user
        super().__init__(
            authenticate=authenticate,
            method=method,
            no_prompt=no_prompt,
            token_path=token_path,
        )

        # Only method "add"can use the MotdManager class
        if self.method not in ["add"]:
            raise dds_cli.exceptions.AuthenticationError(f"Unauthorized method: '{self.method}'")

    def add_new_motd(self, message):
        """Add a new motd."""
        err_message = "Failed adding a new MOTD"

        try:
            response = requests.post(
                DDSEndpoint.ADD_NEW_MOTD,
                json={"message": message},
                headers=self.token,
                timeout=DDSEndpoint.TIMEOUT,
            )
            response_json = response.json()
        except requests.exceptions.RequestException as err:
            raise dds_cli.exceptions.ApiRequestError(
                message=(
                    err_message
                    + (
                        ": The database seems to be down."
                        if isinstance(err, requests.exceptions.ConnectionError)
                        else "."
                    )
                )
            )
        except simplejson.JSONDecodeError as err:
            raise dds_cli.exceptions.ApiResponseError(message=str(err))

        # Check if response is ok.
        if not response.ok:
            if response.status_code == http.HTTPStatus.INTERNAL_SERVER_ERROR:
                raise dds_cli.exceptions.ApiResponseError(
                    message=f"{err_message}: {response.reason}"
                )

            cred_err_message = (
                ": Only Super Admin can add a MOTD"
                if response.status_code == http.HTTPStatus.FORBIDDEN
                else ""
            )
            raise dds_cli.exceptions.DDSCLIException(
                message=f"{response_json.get('message', 'Unexpected error!')}{cred_err_message}"
            )
        LOG.info("A new MOTD was added to the database")
