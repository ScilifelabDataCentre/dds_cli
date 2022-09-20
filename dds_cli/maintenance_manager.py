"""Maintenance Manager module."""

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


class MaintenanceManager(dds_cli.base.DDSBaseClass):
    """Admin class for managing system maintenance mode."""

    def __init__(
        self,
        authenticate: bool = True,
        method: str = "off",
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

        # Only methods "on" and "off" can use the Maintenance class
        if self.method not in ["on", "off"]:
            raise dds_cli.exceptions.AuthenticationError(f"Unauthorized method: '{self.method}'")

    def maintenance_on(self) -> None:
        """Change Maintenance mode."""
        response_json, _ = dds_cli.utils.perform_request(
            endpoint=DDSEndpoint.MAINTENANCE,
            headers=self.token,
            method="put",
            json={"state": "on"},
            error_message="Failed setting maintenance mode",
        )

        response_message = response_json.get(
            "message", "No response. Cannot confirm setting maintenance mode."
        )
        LOG.info(response_message)

    def maintenance_off(self) -> None:
        """Change Maintenance mode."""
        response_json, _ = dds_cli.utils.perform_request(
            endpoint=DDSEndpoint.MAINTENANCE,
            headers=self.token,
            method="put",
            json={"state": "off"},
            error_message="Failed setting maintenance mode",
        )

        response_message = response_json.get(
            "message", "No response. Cannot confirm setting maintenance mode."
        )
        LOG.info(response_message)
