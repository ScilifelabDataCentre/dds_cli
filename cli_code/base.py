

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import dataclasses
import inspect
import logging
import functools
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


def attempted_operation():
    """Gets the command entered by the user (e.g. put)."""

    curframe = inspect.currentframe()
    return inspect.getouterframes(curframe, 2)[4].function


class DDSBaseClass:
    """Data Delivery System base class. For common operations."""

    def __init__(self, username=None, password=None, config=None, project=None):
        # Get attempted operation e.g. put/ls
        self.method = attempted_operation()

        # Verify that user entered enough info
        username, password, self.project = \
            self.verify_input(username=username, password=password,
                              config=config, project=project)

        # Authenticate the user and get the token
        self.user = user.User(username=username, password=password)
        self.token = self.user.token

    def verify_input(self, username=None, password=None, config=None,
                     project=None):
        """Verifies that the users input is valid and fully specified."""
        # Get contents from file
        if config is not None:
            # Get contents from file
            contents = fh.FileHandler.extract_config(configfile=config)

            # Get user credentials and project info if not already specified
            if username is None and "username" in contents:
                username = contents["username"]
            if project is None and "project" in contents:
                project = contents["project"]
            if password is None and "password" in contents:
                password = contents["password"]

        # Username and project info is minimum required info
        if self.method == "put" and project is None:
            sys.exit("Data Delivery System project information is missing.")
        if username is None:
            sys.exit("Data Delivery System options are missing.")

        # Set password if missing
        if password is None:
            # password = getpass.getpass()
            password = "password"   # TODO: REMOVE - ONLY FOR DEV

        return username, password, project
    # def __init__(self, func):
    #     functools.update_wrapper(self, func)
    #     self.func = func

    # def __call__(self, *args, **kwargs):
    #     log.debug(args)
    #     log.debug(kwargs)
    #     return self.func(*args, **kwargs)

    # method: str = dataclasses.field(default_factory=attempted_operation)
    # username: dataclasses.InitVar[str] = None

    # def __post_init__(self, username):
    #     log.debug(username)
