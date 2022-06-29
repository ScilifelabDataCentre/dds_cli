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
        response_json, _ = dds_cli.utils.perform_request(
            endpoint=DDSEndpoint.MOTD,
            headers=self.token,
            method="post",
            json={"message": message},
            error_message="Failed adding a new MOTD",
        )

        LOG.info("A new MOTD was added to the database")

    @staticmethod
    def get_latest_motd():
        """Get the latest MOTD from dabase"""
        try:
            response_json, _ = dds_cli.utils.perform_request(
                endpoint=DDSEndpoint.MOTD,
                method="get",
                error_message="Failed getting MOTD",
            )
        except:
            pass
        else:
            return response_json.get("message")
