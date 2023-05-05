"""Unit Manager module."""

####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
###################################################################################################

# Standard library
import logging

# Installed

# Own modules
import dds_cli
import dds_cli.auth
import dds_cli.base
import dds_cli.exceptions
import dds_cli.utils


####################################################################################################
# START LOGGING CONFIG ###################################################### START LOGGING CONFIG #
####################################################################################################

LOG = logging.getLogger(__name__)


####################################################################################################
# CLASSES ################################################################################ CLASSES #
####################################################################################################


class UnitManager(dds_cli.base.DDSBaseClass):
    """Admin class for managing Units."""

    def __init__(
        self,
        authenticate: bool = True,
        method: str = "ls",
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

        # Only methods "add", "delete" and "revoke" can use the AccountManager class
        if self.method not in ["ls"]:
            raise dds_cli.exceptions.AuthenticationError(f"Unauthorized method: '{self.method}'")

    def list_all_units(self):
        """Get info about all units."""
        response, _ = dds_cli.utils.perform_request(
            endpoint=dds_cli.DDSEndpoint.LIST_UNITS_ALL,
            method="get",
            headers=self.token,
            error_message="Failed getting units from API",
        )

        # Get items from response
        units, keys = dds_cli.utils.get_required_in_response(
            keys=["units", "keys"], response=response
        )

        # Sort users according to name
        units = dds_cli.utils.sort_items(items=units, sort_by="Name")

        # Create table
        table = dds_cli.utils.create_table(
            title="Units within the DDS.",
            columns=keys,
            rows=units,
            ints_as_string=False,
            caption="All units within the DDS.",
        )

        # Print out table
        dds_cli.utils.print_or_page(item=table)
