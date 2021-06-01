"""DDS CLI."""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard Library
import glob
import logging
import os
import pathlib
import sys

# Installed
import rich
import yaml
from rich.logging import RichHandler

# Own modules

###############################################################################
# PROJECT SPEC ################################################# PROJECT SPEC #
###############################################################################

__title__ = "Data Delivery System"
__version__ = "0.2"
__author__ = "SciLifeLab Data Centre"
__author_email__ = ""
__license__ = "MIT"

PROG = "dds"

###############################################################################
# LOGGING ########################################################### LOGGING #
###############################################################################


def setup_custom_logger(filename: str = None, debug: bool = False):
    """Creates logger and sets the levels."""

    config = {
        "version": 1,
        "formatters": {
            "logformatter": {"format": "%(asctime)s :: %(name)s - %(lineno)d :: %(message)s"}
        },
        "handlers": {},
    }

    handlers = []
    if debug:
        handlers.append("console")
        config["handlers"].update(
            **{
                "console": {
                    "class": "rich.logging.RichHandler",
                    "level": "DEBUG",
                    "formatter": "logformatter",
                }
            }
        )

    if filename:
        handlers.append("file")
        config["handlers"].update(
            **{
                "file": {
                    "class": "logging.FileHandler",
                    "level": "DEBUG" if debug else "INFO",
                    "formatter": "logformatter",
                    "filename": filename,
                }
            }
        )

    config.update(
        {
            "root": {"level": "DEBUG", "handlers": handlers},
            "loggers": {
                os.path.splitext(x)[0].replace(os.sep, "."): {
                    "handlers": handlers,
                    "propagate": False,
                }
                for x in glob.glob(f"{__name__}/*.py")
                if x != __name__
            },
        }
    )

    logging.config.dictConfig(config)

    # Log version
    LOG = logging.getLogger(__name__)
    LOG.info("DDS Version: %s", __version__)


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
