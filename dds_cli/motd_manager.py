"""Motd Manager module."""

####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
###################################################################################################

# Standard library
import logging
from typing import Optional

# Installed

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
    def list_all_active_motds(table: bool = False) -> Optional[list]:
        """Get all active MOTDs.
        When called from "dds modt ls" with table=True, the function will print a table of the MOTDs,
        else it will return a list of MOTDs. The function runs on every dds call.

        :param table: Whether to print a table of the MOTDs.
        :return: A list of MOTDs if table is False, otherwise None.
        """

        response, _ = dds_cli.utils.perform_request(
            endpoint=dds_cli.DDSEndpoint.MOTD,
            method="get",
            error_message="Failed getting MOTDs from API",
        )

        motd = response.get("motds")

        if not motd:
            raise dds_cli.exceptions.NoMOTDsError(
                message=response.get("message", "No motds or info message returned from API.")
            )

        motds, keys = dds_cli.utils.get_required_in_response(
            keys=["motds", "keys"], response=response
        )

        motds = dds_cli.utils.sort_items(items=motds, sort_by="Created")

        if table:
            table = dds_cli.utils.create_table(
                title="Active MOTDs.",
                columns=keys,
                rows=motds,
                ints_as_string=True,
                caption="Active MOTDs.",
            )

            dds_cli.utils.print_or_page(item=table)
            return None

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

    def send_motd(self, motd_id: int, unit_only=False) -> None:
        """Send specific MOTD to users."""
        response_json, _ = dds_cli.utils.perform_request(
            endpoint=DDSEndpoint.MOTD_SEND,
            headers=self.token,
            method="post",
            json={"motd_id": motd_id, "unit_only": unit_only},
            error_message="Failed sending the MOTD to users",
        )

        response_message = response_json.get(
            "message", "No response. Cannot confirm that MOTDs have been sent."
        )
        LOG.info(response_message)
