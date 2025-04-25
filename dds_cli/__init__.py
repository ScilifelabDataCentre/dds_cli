# pylint: skip-file
"""DDS CLI."""

import datetime
import os
import pathlib
import prompt_toolkit
import rich.console
import sys

from dds_cli.version import __version__ as version_number

###############################################################################
# PROJECT SPEC ################################################# PROJECT SPEC #
###############################################################################

__title__ = "Data Delivery System"
__version__ = version_number
__url__ = "https://delivery.scilifelab.se/"
__author__ = "SciLifeLab Data Centre"
__author_email__ = "datacentre@scilifelab.se"
__license__ = "MIT"
__all__ = [
    "DDS_METHODS",
    "DDS_DIR_REQUIRED_METHODS",
    "DDS_KEYS_REQUIRED_METHODS",
    "DDSEndpoint",
    "FileSegment",
    "dds_questionary_styles",
]


###############################################################################
# VARIABLES ####################################################### VARIABLES #
###############################################################################

# Keep track of all allowed methods
DDS_METHODS = ["put", "get", "ls", "rm", "create", "add", "delete", "on", "off"]

# Methods to which a directory created by DDS
DDS_DIR_REQUIRED_METHODS = ["put", "get"]

# Methods which require a project ID
DDS_KEYS_REQUIRED_METHODS = ["put", "get"]

# Token related variables
TOKEN_FILE = pathlib.Path(os.path.expanduser("~/.dds_cli_token"))
TOKEN_EXPIRATION_WARNING_THRESHOLD = datetime.timedelta(hours=6)


###############################################################################
# CLASSES ########################################################### CLASSES #
###############################################################################


class DDSEndpoint:
    """Defines all DDS urls."""

    # Base url - local or remote
    BASE_ENDPOINT_LOCAL = "http://127.0.0.1:5000/api/v1"
    BASE_ENDPOINT_DOCKER = "http://dds_backend:5000/api/v1"
    BASE_ENDPOINT_REMOTE = "https://delivery.scilifelab.se/api/v1"
    BASE_ENDPOINT_REMOTE_TEST = "https://testing.delivery.scilifelab.se/api/v1"
    BASE_ENDPOINT_REMOTE_DEV = "https://dev.delivery.scilifelab.se/api/v1"
    if os.getenv("DDS_CLI_ENV") == "development":
        BASE_ENDPOINT = BASE_ENDPOINT_LOCAL
    elif os.getenv("DDS_CLI_ENV") == "docker-dev":
        BASE_ENDPOINT = BASE_ENDPOINT_DOCKER
    elif os.getenv("DDS_CLI_ENV") == "test-instance":
        BASE_ENDPOINT = BASE_ENDPOINT_REMOTE_TEST
    elif os.getenv("DDS_CLI_ENV") == "dev-instance":
        BASE_ENDPOINT = BASE_ENDPOINT_REMOTE_DEV
    else:
        BASE_ENDPOINT = BASE_ENDPOINT_REMOTE

    # User management
    USER_ADD = BASE_ENDPOINT + "/user/add"
    USER_DELETE = BASE_ENDPOINT + "/user/delete"
    USER_DELETE_SELF = BASE_ENDPOINT + "/user/delete_self"
    REVOKE_PROJECT_ACCESS = BASE_ENDPOINT + "/user/access/revoke"
    DISPLAY_USER_INFO = BASE_ENDPOINT + "/user/info"
    USER_ACTIVATION = BASE_ENDPOINT + "/user/activation"
    USER_ACTIVATE_TOTP = BASE_ENDPOINT + "/user/totp/activate"
    USER_ACTIVATE_HOTP = BASE_ENDPOINT + "/user/hotp/activate"
    USER_EMAILS = BASE_ENDPOINT + "/user/emails"

    # Authentication - user and project
    ENCRYPTED_TOKEN = BASE_ENDPOINT + "/user/encrypted_token"
    SECOND_FACTOR = BASE_ENDPOINT + "/user/second_factor"

    # S3Connector keys
    S3KEYS = BASE_ENDPOINT + "/s3/proj"

    # File related urls
    FILE_NEW = BASE_ENDPOINT + "/file/new"
    FILE_MATCH = BASE_ENDPOINT + "/file/match"
    FILE_INFO = BASE_ENDPOINT + "/file/info"
    FILE_INFO_ALL = BASE_ENDPOINT + "/file/all/info"
    FILE_UPDATE = BASE_ENDPOINT + "/file/update"
    FILE_ADD_FAILED = BASE_ENDPOINT + "/file/failed/add"

    # Project specific urls
    PROJ_ACCESS = BASE_ENDPOINT + "/proj/access"
    PROJ_BUSY_ANY = BASE_ENDPOINT + "/proj/busy/any"
    PROJ_INFO = BASE_ENDPOINT + "/proj/info"

    # Listing urls
    LIST_PROJ = BASE_ENDPOINT + "/proj/list"
    LIST_FILES = BASE_ENDPOINT + "/files/list"
    LIST_PROJ_USERS = BASE_ENDPOINT + "/proj/users"
    LIST_UNITS_ALL = BASE_ENDPOINT + "/unit/info/all"
    LIST_USERS = BASE_ENDPOINT + "/users"
    LIST_INVITED_USERS = BASE_ENDPOINT + "/user/invites"
    # LIST_USERS_ALL = BASE_ENDPOINT + "/users"

    # Deleting urls
    REMOVE_PROJ_CONT = BASE_ENDPOINT + "/proj/rm"
    REMOVE_FILE = BASE_ENDPOINT + "/file/rm"
    REMOVE_FOLDER = BASE_ENDPOINT + "/file/rmdir"

    # Encryption keys
    PROJ_PUBLIC = BASE_ENDPOINT + "/proj/public"
    PROJ_PRIVATE = BASE_ENDPOINT + "/proj/private"

    # Display facility usage
    USAGE = BASE_ENDPOINT + "/usage"
    INVOICE = BASE_ENDPOINT + "/invoice"

    # Project creation urls
    CREATE_PROJ = BASE_ENDPOINT + "/proj/create"

    # Project status updation
    UPDATE_PROJ_STATUS = BASE_ENDPOINT + "/proj/status"

    # MOTD
    MOTD = BASE_ENDPOINT + "/motd"
    MOTD_SEND = BASE_ENDPOINT + "/motd/send"

    # Find user
    USER_FIND = BASE_ENDPOINT + "/user/find"

    # Deactivate TOTP
    TOTP_DEACTIVATE = BASE_ENDPOINT + "/user/totp/deactivate"

    # Activate / deactivate Maintenance mode
    MAINTENANCE = BASE_ENDPOINT + "/maintenance"

    # Get statistics
    STATS = BASE_ENDPOINT + "/stats"

    TIMEOUT = 120


class FileSegment:
    """Defines information on signatures, file chunks, etc."""

    DDS_SIGNATURE = b"DelSys"
    SEGMENT_SIZE_RAW = 65536  # Size of chunk to read from raw file
    SEGMENT_SIZE_CIPHER = SEGMENT_SIZE_RAW + 16  # Size of chunk to read from encrypted file


# Custom styles for questionary
dds_questionary_styles = prompt_toolkit.styles.Style(
    [
        ("qmark", "fg:ansiblue bold"),  # token in front of the question
        ("question", "bold"),  # question text
        ("answer", "fg:ansigreen nobold bg:"),  # submitted answer text behind the question
        ("pointer", "fg:ansiyellow bold"),  # pointer used in select and checkbox prompts
        ("highlighted", "fg:ansiblue bold"),  # pointed-at choice in select and checkbox prompts
        ("selected", "fg:ansiyellow noreverse bold"),  # style for a selected item of a checkbox
        ("separator", "fg:ansiblack"),  # separator in lists
        ("instruction", ""),  # user instructions for select, rawselect, checkbox
        ("text", ""),  # plain text
        ("disabled", "fg:gray italic"),  # disabled choices for select and checkbox prompts
        ("choice-default", "fg:ansiblack"),
        ("choice-default-changed", "fg:ansiyellow"),
        ("choice-required", "fg:ansired"),
    ]
)

# Determine if the user is on an old terminal without proper Unicode support
dds_on_legacy_console = rich.console.detect_legacy_windows()

# Required to make the standalone executables build with PyInstaller work.
if __name__ == "__main__":
    from dds_cli.__main__ import dds_main

    if getattr(sys, "frozen", False):
        dds_main(sys.argv[1:])
    else:
        dds_main()
