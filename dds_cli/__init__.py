"""DDS CLI."""

import os
import pkg_resources

###############################################################################
# PROJECT SPEC ################################################# PROJECT SPEC #
###############################################################################

__title__ = "Data Delivery System"
__version__ = pkg_resources.get_distribution("dds_cli").version
__url__ = "https://www.scilifelab.se/data"
__author__ = "SciLifeLab Data Centre"
__author_email__ = "datacentre@scilifelab.se"
__license__ = "MIT"


###############################################################################
# CLASSES ########################################################### CLASSES #
###############################################################################


class DDSEndpoint:
    """Defines all DDS urls."""

    # Base url - local or remote
    BASE_ENDPOINT_LOCAL = "http://127.0.0.1:5000/api/v1"
    BASE_ENDPOINT_REMOTE = "https://dds.dckube.scilifelab.se/api/v1"
    BASE_ENDPOINT = (
        BASE_ENDPOINT_LOCAL if os.getenv("DDS_CLI_ENV") == "development" else BASE_ENDPOINT_REMOTE
    )

    # Authentication - user and project
    AUTH = BASE_ENDPOINT + "/user/auth"
    AUTH_PROJ = BASE_ENDPOINT + "/proj/auth"

    # S3Connector keys
    S3KEYS = BASE_ENDPOINT + "/s3/proj"

    # File related urls
    FILE_NEW = BASE_ENDPOINT + "/file/new"
    FILE_MATCH = BASE_ENDPOINT + "/file/match"
    FILE_INFO = BASE_ENDPOINT + "/file/info"
    FILE_INFO_ALL = BASE_ENDPOINT + "/file/all/info"
    FILE_UPDATE = BASE_ENDPOINT + "/file/update"

    # Project specific urls
    PROJECT_SIZE = BASE_ENDPOINT + "/proj/size"

    # Listing urls
    LIST_PROJ = BASE_ENDPOINT + "/proj/list"
    LIST_FILES = BASE_ENDPOINT + "/files/list"

    # Deleting urls
    REMOVE_PROJ_CONT = BASE_ENDPOINT + "/proj/rm"
    REMOVE_FILE = BASE_ENDPOINT + "/file/rm"
    REMOVE_FOLDER = BASE_ENDPOINT + "/file/rmdir"

    # Encryption keys
    PROJ_PUBLIC = BASE_ENDPOINT + "/proj/public"
    PROJ_PRIVATE = BASE_ENDPOINT + "/proj/private"

    TIMEOUT = 5


class FileSegment:
    """Defines information on signatures, file chunks, etc."""

    DDS_SIGNATURE = b"DelSys"
    SEGMENT_SIZE_RAW = 65536  # Size of chunk to read from raw file
    SEGMENT_SIZE_CIPHER = SEGMENT_SIZE_RAW + 16  # Size of chunk to read from encrypted file
