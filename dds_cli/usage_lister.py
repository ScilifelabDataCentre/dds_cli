"""Usage Displayer -- Shows the usage per facility and project."""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import logging
import pathlib

# Installed
import requests
import simplejson
from rich.console import Console
from rich.table import Table

# Own modules
from dds_cli import base
from dds_cli import exceptions
from dds_cli import DDSEndpoint

###############################################################################
# START LOGGING CONFIG ################################# START LOGGING CONFIG #
###############################################################################

LOG = logging.getLogger(__name__)

###############################################################################
# CLASSES ########################################################### CLASSES #
###############################################################################


class UsageLister(base.DDSBaseClass):
    """Data lister class."""

    def __init__(
        self,
        username: str = None,
        config: pathlib.Path = None,
        project: str = None,
        project_level: bool = False,
    ):

        # Initiate DDSBaseClass to authenticate user
        super().__init__(username=username, config=config)

        # Only method "usage" can use the DataLister class
        if self.method != "usage":
            raise exceptions.AuthenticationError(f"Unauthorized method: '{self.method}'")
