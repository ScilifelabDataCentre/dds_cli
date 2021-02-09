"""DDS CLI."""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard Library
import logging
import sys

# Installed

# Own modules

###############################################################################
# PROJECT SPEC ################################################# PROJECT SPEC #
###############################################################################

__title__ = "Data Delivery System"
__version__ = "0.1"
__author__ = "SciLifeLab Data Centre"
__author_email__ = ""
__license__ = "MIT"

PROG = "ds_deliver"

# Logging
LOG = logging.getLogger(__name__)


def setup_custom_logger(filename: str = "", debug: bool = False):
    """Creates log file

    Args:
        filename:           Path to wished log file

    Returns:
        Logger:     Configured logger

    Raises:
        Exception:   Logging to file or console failed
    """

    logger = logging.getLogger(__name__)

    # Config file logger
    if filename != "":
        try:
            file_handler = logging.FileHandler(filename=filename)
            fh_formatter = logging.Formatter("%(asctime)s::%(levelname)s::" +
                                            "%(name)s::%(lineno)d::%(message)s")
            file_handler.setFormatter(fh_formatter)
            file_handler.setLevel(logging.INFO)
            logger.addHandler(file_handler)
        except OSError as ose:
            sys.exit(f"Logging to file failed: {ose}")

    # Config file logger
    if debug:
        try:
            stream_handler = logging.StreamHandler()
            sh_formatter = logging.Formatter("%(levelname)s::%(name)s::" +
                                            "%(lineno)d::%(message)s")
            stream_handler.setFormatter(sh_formatter)
            logger.addHandler(stream_handler)
        except OSError as ose:
            sys.exit(f"Logging to console failed: {ose}")

    return logger

###############################################################################
# CLASSES ########################################################### CLASSES #
###############################################################################


class DDSEndpoint:
    """Defines all DDS urls."""

    BASE_ENDPOINT_LOCAL = "http://127.0.0.1:5000/api/v1"
    BASE_ENDPOINT_REMOTE = "https://dds.dckube.scilifelab.se/api/v1"

    BASE_ENDPOINT = BASE_ENDPOINT_LOCAL

    AUTH = BASE_ENDPOINT + "/user/auth"
    AUTH_PROJ = BASE_ENDPOINT + "/proj/auth"


class FileSegment:
    """Defines information on signatures, file chunks, etc."""

    DDS_SIGNATURE = b"DelSys"
    SEGMENT_SIZE_RAW = 65536
    SEGMENT_SIZE_CIPHER = SEGMENT_SIZE_RAW + 16


class StringFormat:
    """Defines different formats for strings, e.g. colors and bold."""

    HEADER = '\033[95m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    DARKCYAN = '\033[36m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

