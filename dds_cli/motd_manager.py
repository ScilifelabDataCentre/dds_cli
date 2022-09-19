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
            raise dds_cli.exceptions.InvalidMethodError(f"Unauthorized method: '{self.method}'")

    def add_new_motd(self, message):
        """Add a new motd."""
        response_json, _ = dds_cli.utils.perform_request(
            endpoint=DDSEndpoint.MOTD,
            headers=self.token,
            method="post",
            json={"message": message},
            error_message="Failed adding a new MOTD",
        )

        response_message = response_json.get(
            "message", "No response. Cannot confirm MOTD creation."
        )
        LOG.info(response_message)

    @staticmethod
    def list_all_active_motds(table=False):
        """Get all active MOTDs."""
        try:
            response, _ = dds_cli.utils.perform_request(
                endpoint=dds_cli.DDSEndpoint.MOTD,
                method="get",
                error_message="Failed getting MOTDs from API",
            )
        except:
            pass
        else:
            # Get items from response
            motd = response.get("motds")
            if not motd:
                message = response.get("message", "No motds or info message returned from API.")
                LOG.info(message)
            else:
                motds, keys = dds_cli.utils.get_required_in_response(
                    keys=["motds", "keys"], response=response
                )
                # Sort the active MOTDs according to date created
                motds = dds_cli.utils.sort_items(items=motds, sort_by="Created")

                # when called from "dds modt ls" with table=True
                if table:
                    # Create table
                    table = dds_cli.utils.create_table(
                        title="Active MOTDs.",
                        columns=keys,
                        rows=motds,
                        ints_as_string=True,
                        caption="Active MOTDs.",
                    )

                    # Print out table
                    dds_cli.utils.print_or_page(item=table)
                else:
                    # on every dds call
                    return motds

    def deactivate_motd(self, motd_id) -> None:
        """Deactivate specific MOTD."""
        response_json, _ = dds_cli.utils.perform_request(
            endpoint=DDSEndpoint.MOTD,
            headers=self.token,
            method="put",
            json={"motd_id": motd_id},
            error_message="Failed deactivating the MOTD",
        )

        response_message = response_json.get(
            "message", "No response. Cannot confirm MOTD deactivation."
        )
        LOG.info(response_message)

    def send_motd(self, motd_id: int) -> None:
        """Send specific MOTD to users."""
        response_json, _ = dds_cli.utils.perform_request(
            endpoint=DDSEndpoint.MOTD_SEND,
            headers=self.token,
            method="post",
            json={"motd_id": motd_id},
            error_message="Failed sending the MOTD to users",
        )

        response_message = response_json.get(
            "message", "No response. Cannot confirm that MOTDs have been sent."
        )
        LOG.info(response_message)
