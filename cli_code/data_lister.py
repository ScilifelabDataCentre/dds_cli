"""Data Lister -- Lists the projects and project content."""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import dataclasses
import logging
import pathlib
import traceback
import sys

# Installed

# Own modules
from cli_code import file_handler as fh
from cli_code import user

###############################################################################
# START LOGGING CONFIG ################################# START LOGGING CONFIG #
###############################################################################

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

###############################################################################
# DECORATORS ##################################################### DECORATORS #
###############################################################################

###############################################################################
# CLASSES ########################################################### CLASSES #
###############################################################################


@dataclasses.dataclass
class DataLister:
    """Data lister class."""

    project: str = None
    config: dataclasses.InitVar[pathlib.Path] = None
    username: dataclasses.InitVar[str] = None
    password: dataclasses.InitVar[str] = None

    # Magic methods ################# Magic methods #
    def __post_init__(self, *args):
        log.debug(args)

        username, password, self.project, args = \
            self.verify_input(user_input=(self.project, ) + args)

        dds_user = user.User(username=username, password=password)
        self.token = dds_user.token

        if self.project is None:
            pass  # TODO (ina): list all projects
        else:
            pass  # List all files in project
        

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if exc_type is not None:
            traceback.print_exception(exc_type, exc_value, tb)
            return False  # uncomment to pass exception through

        return True

    # Static methods ############### Static methods #
    @staticmethod
    def verify_input(user_input):
        """Verifies that the required information is specified."""

        project, config, username, password, *args = user_input

        # Get contents from file
        if config is not None:
            contents = fh.FileHandler.extract_config(configfile=config)

            log.debug(contents)
            if username is None and "username" in contents:
                username = contents["username"]
            if password is None and "password" in contents:
                password = contents["password"]

        if username is None:
            sys.exit("Data Delivery System username is missing.")

        if password is None:
            # password = getpass.getpass()
            password = "password"   # TODO: REMOVE - ONLY FOR DEV

        return username, password, project, args
