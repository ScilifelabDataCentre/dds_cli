"""Data Delivery System Project info manager."""
import logging

# Installed
import requests
import simplejson
import pytz
import tzlocal
import datetime

# Own modules
from dds_cli import base
from dds_cli import exceptions
from dds_cli import DDSEndpoint
import dds_cli.utils

###############################################################################
# START LOGGING CONFIG ################################# START LOGGING CONFIG #
###############################################################################

LOG = logging.getLogger(__name__)


###############################################################################
# CLASSES ########################################################### CLASSES #
###############################################################################


class ProjectInfoManager(base.DDSBaseClass):
    """Project info manager class."""

    def __init__(
        self,
        project: str,
        no_prompt: bool = False,
        token_path: str = None,
    ):
        """Handle actions regarding project info in the cli."""
        # Initiate DDSBaseClass to authenticate user
        super().__init__(
            no_prompt=no_prompt,
            method_check=False,
            token_path=token_path,
        )
        self.project = project

    # Public methods ###################### Public methods #
    def update_info(self, title=None, description=None, pi=None):
        """Update project info"""

        info_items = {}
        if title:
            info_items["title"] = title
        if description:
            info_items["description"] = description
        if pi:
            info_items["pi"] = pi

        response_json, _ = dds_cli.utils.perform_request(
            endpoint=DDSEndpoint.PROJ_INFO,
            headers=self.token,
            method="post",
            params={"project": self.project},
            json=info_items,
            error_message="Failed to update project info",
        )

        dds_cli.utils.console.print(f"Project {response_json.get('message')}")


